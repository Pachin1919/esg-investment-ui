"""Scorer agent: applies the versioned talk/walk rubric to every section (LLM)."""

from __future__ import annotations

import pandas as pd

from esgx.measures import talkwalk as tw
from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    docs = task.ctx.get("documents", pd.DataFrame())
    agent = task.agent
    client = task.tools.llm_client(task.mode, agent)
    system = task.tools.rubric_system_prompt(agent.role_prompt, agent.name)
    talk_w = task.param("talk_weights") or tw.TALK_WEIGHTS
    walk_w = task.param("walk_weights") or tw.WALK_WEIGHTS
    rows = []
    for i, (_, row) in enumerate(docs.iterrows(), 1):
        year = pd.to_datetime(row["period"]).year if row.get("period") else pd.to_datetime(row["filing_date"]).year
        d = task.tools.llm_score_section(client, row["firm_name"], row, task.ctx.get("hard_data", {}).get((row["firm_id"], year), {}),
                                         max_chars=task.ctx.get("max_chars", 60000), system=system, talk_weights=talk_w, walk_weights=walk_w)
        rows.append(d)
        if d.get("skipped"):
            task.log(f"[{i}/{len(docs)}] {row['firm_id']} {row['form']} {row['period']} {row['section']}: skipped ({d.get('skip_reason')})")
        else:
            task.log(f"[{i}/{len(docs)}] {row['firm_id']} {row['form']} {row['period']} {row['section']}: talk {d['talk']:.2f} walk {d['walk']:.2f}")
    scored = pd.DataFrame(rows)
    task.ctx["scored"] = scored
    n_ok = int((~scored["skipped"]).sum()) if len(scored) else 0
    return {"scored": n_ok, "skipped": int(len(scored) - n_ok),
            "tokens_in": int(scored.get("usage_input_tokens", pd.Series(dtype=float)).sum()),
            "tokens_out": int(scored.get("usage_output_tokens", pd.Series(dtype=float)).sum())}


AGENT = AgentDefinition(
    id="score_talkwalk", kind="score_talkwalk", name="Talk / walk scorer",
    role="Scorer",
    description="Structured-output rubric: 5 talk and 6 walk sub-scores, commitments, quotes, summary. Cached per filing, section, rubric version, model and prompt variant.",
    tools=("llm_client", "rubric_system_prompt", "llm_score_section"),
    inputs=("ctx.documents", "ctx.hard_data", "ctx.max_chars"), outputs=("ctx.scored",),
    llm=True, default_model=tw.DEFAULT_MODEL, default_effort="medium",
    default_params={"talk_weights": tw.TALK_WEIGHTS, "walk_weights": tw.WALK_WEIGHTS},
    run=run,
)
