"""Agentic pipeline orchestrator.

Stages are owned by agents defined under `pipeline/agents/<id>/` (role, allowed tools, run function);
tools live under `pipeline/tools/`. This module only sequences them: build the default spec from the
registry, run a spec stage by stage in a background thread, keep run state, estimate cost, and read /
write saved specs. No measurement logic lives here.

Modes: dry_run (heuristics, free), cache_only (cached LLM answers, misses skipped), live (paid).
"""

from __future__ import annotations

import json
import threading
import traceback
from datetime import UTC, datetime
from typing import Any

from esgx.agents.state import RUN_DIR, RunState
from esgx.config import ROOT
from pipeline.agents import AGENTS, StageTask
from pipeline.spec import (  # noqa: F401  (re-exported for the API)
    AgentSpec,
    Mode,
    PipelineSpec,
    StageKind,
    StageSpec,
)

CONFIG_DIR = ROOT / "configs" / "pipeline"

# Observed in the XOM pilot (session 2): 12 sections, ~0.95 USD, claude-opus-5 effort medium.
USD_PER_SECTION = 0.08
USD_PER_REVIEW = 0.03


def default_pipeline() -> PipelineSpec:
    """The pipeline as the agents define it, in registry order."""
    return PipelineSpec(
        name="default",
        description="EDGAR 10-K sections -> climate passages + GHGRP hard data -> talk/walk agent -> "
                    "dictionary measures -> reviewer agent -> firm-year aggregation.",
        stages=[a.default_stage() for a in AGENTS.values()],
    )


def estimate_cost(spec: PipelineSpec, n_sections: int, n_firm_years: int) -> dict[str, float]:
    on = {s.kind for s in spec.stages if s.enabled}
    scorer = USD_PER_SECTION * n_sections if "score_talkwalk" in on else 0.0
    review = USD_PER_REVIEW * n_firm_years if "review" in on else 0.0
    return {"scorer_usd": round(scorer, 2), "review_usd": round(review, 2), "total_usd": round(scorer + review, 2)}


class Orchestrator:
    """Runs a PipelineSpec stage by stage; each stage is delegated to its agent with a ToolBox
    restricted to that agent's tools."""

    def __init__(self) -> None:
        self.runs: dict[str, RunState] = {}
        self._lock = threading.Lock()

    def start(self, spec: PipelineSpec, tickers: list[str], mode: Mode, blocking: bool = False) -> RunState:
        run = RunState(spec, tickers, mode, RUN_DIR)
        with self._lock:
            self.runs[run.id] = run
        if blocking:
            self._execute(run)
        else:
            threading.Thread(target=self._execute, args=(run,), daemon=True).start()
        return run

    def get(self, run_id: str) -> RunState | None:
        return self.runs.get(run_id)

    def list(self) -> list[dict[str, Any]]:
        return [r.to_dict(full=False) for r in sorted(self.runs.values(), key=lambda r: r.started, reverse=True)]

    def _execute(self, run: RunState) -> None:
        run.status = "running"
        ctx: dict[str, Any] = {}
        try:
            run.dir.mkdir(parents=True, exist_ok=True)
            for stage in run.spec.stages:
                if not stage.enabled:
                    run.stages[stage.id] = {"status": "skipped"}
                    continue
                agent = AGENTS[stage.kind]
                run.stages[stage.id] = {"status": "running", "agent": agent.id}
                t0 = datetime.now(tz=UTC)
                task = StageTask(run=run, spec=run.spec, stage=stage, mode=run.mode, tickers=run.tickers,
                                 ctx=ctx, run_dir=run.dir, tools=agent.toolbox())
                summary = agent.run(task) or {}
                run.stages[stage.id] = {"status": "done", "agent": agent.id,
                                        "seconds": round((datetime.now(tz=UTC) - t0).total_seconds(), 1), **summary}
            run.results = ctx.get("results", {})
            run.status = "done"
        except Exception as e:  # noqa: BLE001 - surfaced to the UI
            run.status = "failed"
            run.error = f"{type(e).__name__}: {e}"
            run.emit("orchestrator", traceback.format_exc()[-1500:])
        finally:
            run.finished = datetime.now(tz=UTC).isoformat(timespec="seconds")
            (run.dir / "run.json").write_text(json.dumps(run.to_dict(), default=str, indent=1))


# ---------------------------------------------------------------- configs on disk
def save_config(name: str, spec: PipelineSpec) -> Any:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-") or "pipeline"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    p = CONFIG_DIR / f"{safe}.json"
    p.write_text(json.dumps(spec.model_dump(), indent=1))
    return p


def list_configs() -> list[dict[str, Any]]:
    if not CONFIG_DIR.exists():
        return []
    out = []
    for p in sorted(CONFIG_DIR.glob("*.json")):
        try:
            spec = PipelineSpec.model_validate_json(p.read_text())
            out.append({"file": p.name, "name": spec.name, "description": spec.description, "stages": len(spec.stages), "spec": spec.model_dump()})
        except Exception as e:  # noqa: BLE001
            out.append({"file": p.name, "name": p.stem, "error": str(e)})
    return out
