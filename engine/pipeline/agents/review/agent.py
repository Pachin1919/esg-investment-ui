"""Reviewer agent: an independent auditor pass over the scorer's output (LLM)."""

from __future__ import annotations

import pandas as pd

from esgx.measures import talkwalk as tw
from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    scored = task.ctx.get("scored")
    if scored is None or scored.empty:
        task.log("nothing to review")
        return {"memos": 0}
    ok = scored[~scored["skipped"]].copy()
    ok["year"] = pd.to_datetime(ok["period"]).dt.year
    memos = []
    for (firm, year), g in ok.groupby(["firm_id", "year"]):
        hd = task.ctx.get("hard_data", {}).get((firm, int(year)), {})
        memo = task.tools.llm_review_memo(task.mode, task.agent, firm, int(year), g, hd)
        memos.append({"firm_id": firm, "year": int(year), **memo})
        task.log(f"{firm} {year}: {len(memo['flags'])} flag(s)")
    task.ctx["memos"] = memos
    return {"memos": len(memos)}


AGENT = AgentDefinition(
    id="review", kind="review", name="Reviewer agent",
    role="Auditor",
    description="Reads every scored section of a firm-year plus the hard data and writes an auditor memo: contradictions, missing baselines, greenwashing flags.",
    tools=("llm_review_memo", "firm_hard_data"),
    inputs=("ctx.scored", "ctx.hard_data"), outputs=("ctx.memos",),
    llm=True, default_model=tw.DEFAULT_MODEL, default_effort="low",
    default_role_prompt="You are a sceptical sustainability auditor. Be concrete, cite the sections, never invent numbers.",
    run=run,
)
