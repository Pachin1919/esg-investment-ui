"""Dictionary agent: cheap text measures next to the LLM scores (deterministic)."""

from __future__ import annotations

import pandas as pd

from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    docs = task.ctx.get("documents", pd.DataFrame())
    scored = task.ctx.get("scored")
    tm = pd.DataFrame([{"accession": r.accession, "section": r.section, **task.tools.text_measures(r.text)} for r in docs.itertuples()]) if len(docs) else pd.DataFrame()
    if scored is not None and len(scored) and len(tm):
        task.ctx["scored"] = scored.merge(tm, on=["accession", "section"], how="left")
    else:
        task.ctx["dictionary"] = tm
    task.log(f"{len(tm)} sections measured (glossiness, sentiment, similarity)")
    return {"sections": len(tm)}


AGENT = AgentDefinition(
    id="dictionary_measures", kind="dictionary_measures", name="Dictionary measures",
    role="Text measurer",
    description="Keyword share, LM sentiment window, forward/realised share, cosine climate similarity, glossiness. No API.",
    tools=("text_measures", "glossiness"),
    inputs=("ctx.documents", "ctx.scored"), outputs=("ctx.scored (+ dictionary columns)",),
    run=run,
)
