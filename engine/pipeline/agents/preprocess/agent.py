"""Preprocessor agent: decides how much of each document the scorer sees (deterministic)."""

from __future__ import annotations

import pandas as pd

from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    task.ctx["max_chars"] = int(task.param("max_chars", 60000))
    task.ctx["min_chars"] = int(task.param("min_chars", 300))
    docs = task.ctx.get("documents", pd.DataFrame())
    if len(docs) and "text" in docs:
        shares = [task.tools.climate_passages(t, max_chars=task.ctx["max_chars"])[1] for t in docs["text"].head(50)]
        task.log(f"climate-passage filter on {len(docs)} sections; mean share of climate paragraphs {sum(shares) / max(1, len(shares)):.2f} (first 50)")
    return {"max_chars": task.ctx["max_chars"], "min_chars": task.ctx["min_chars"]}


AGENT = AgentDefinition(
    id="preprocess", kind="preprocess", name="Preprocess",
    role="Preprocessor",
    description="Keep paragraphs mentioning climate terms plus neighbours; cap characters per section; skip sections that end up too short.",
    tools=("climate_passages", "text_measures"),
    inputs=("ctx.documents",), outputs=("ctx.max_chars", "ctx.min_chars"),
    default_params={"max_chars": 60000, "min_chars": 300},
    run=run,
)
