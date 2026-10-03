"""Aggregator agent: document scores -> firm-year pillars, run outputs, optional publish (deterministic)."""

from __future__ import annotations

import pandas as pd

from esgx.config import ROOT
from esgx.measures import talkwalk as tw
from pipeline.agents.base import AgentDefinition, StageTask
from pipeline.tools.storage import to_records


def run(task: StageTask) -> dict:
    scored = task.ctx.get("scored")
    fw = task.param("form_weights") or tw.FORM_WEIGHTS
    fy = task.tools.aggregate_firm_year(scored, form_weights=fw) if scored is not None and len(scored) else pd.DataFrame()
    if scored is not None:
        task.tools.write_run_output(task.run_dir, "documents", scored)
    task.tools.write_run_output(task.run_dir, "firm_year", fy)
    task.tools.write_run_output(task.run_dir, "memos", task.ctx.get("memos", []))
    sources = task.ctx.get("sources")
    if sources is not None and len(sources):
        task.tools.write_run_output(task.run_dir, "sources", sources)
    drop = [c for c in ("evidence_talk", "evidence_walk", "commitments") if scored is not None and c in scored]
    task.ctx["results"] = {
        "firm_years": to_records(fy),
        "documents": to_records(scored.drop(columns=drop)) if scored is not None and len(scored) else [],
        "memos": task.ctx.get("memos", []),
        "sources": to_records(sources) if sources is not None else [],
        "dir": str(task.run_dir.relative_to(ROOT)) if task.run_dir.is_relative_to(ROOT) else str(task.run_dir),
    }
    if task.param("publish"):
        task.tools.publish_talkwalk(scored, fy, task.spec.universe)
        task.log(f"published to outputs/talkwalk_*_{task.spec.universe}.csv")
    task.log(f"{len(fy)} firm-years written to {task.ctx['results']['dir']}")
    return {"firm_years": len(fy), "published": bool(task.param("publish"))}


AGENT = AgentDefinition(
    id="aggregate", kind="aggregate", name="Aggregate to firm-year",
    role="Aggregator",
    description="Climate-relevance-weighted mean per firm and fiscal year, equal form weights. Writes CSVs to outputs/pipeline_runs/<run>/; publishes to the dashboard tables only on request.",
    tools=("aggregate_firm_year", "write_run_output", "publish_talkwalk"),
    inputs=("ctx.scored", "ctx.memos", "ctx.sources"), outputs=("ctx.results", "outputs/pipeline_runs/<run>/"),
    default_params={"form_weights": tw.FORM_WEIGHTS, "publish": False},
    run=run,
)
