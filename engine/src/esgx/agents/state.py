"""Run state for one pipeline execution: status, per-stage summaries, log, results, output dir."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from esgx.config import OUTPUT_DIR
from pipeline.spec import Mode, PipelineSpec

RUN_DIR = OUTPUT_DIR / "pipeline_runs"


class RunState:
    def __init__(self, spec: PipelineSpec, tickers: list[str], mode: Mode, run_dir: Path = RUN_DIR):
        self.id = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.spec, self.tickers, self.mode = spec, tickers, mode
        self.status = "queued"
        self.started = datetime.now(tz=UTC).isoformat(timespec="seconds")
        self.finished: str | None = None
        self.log: list[dict[str, str]] = []
        self.stages: dict[str, dict[str, Any]] = {s.id: {"status": "pending"} for s in spec.stages}
        self.results: dict[str, Any] = {}
        self.error: str | None = None
        self.dir = run_dir / self.id

    def emit(self, stage: str, msg: str) -> None:
        self.log.append({"t": datetime.now(tz=UTC).isoformat(timespec="seconds"), "stage": stage, "msg": msg})

    def to_dict(self, full: bool = True) -> dict[str, Any]:
        d = {"id": self.id, "status": self.status, "mode": self.mode, "tickers": self.tickers,
             "started": self.started, "finished": self.finished, "error": self.error,
             "spec_name": self.spec.name, "stages": self.stages}
        if full:
            d.update({"log": self.log, "results": self.results, "spec": self.spec.model_dump()})
        return d
