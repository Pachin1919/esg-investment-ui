"""LLM tools: the talk/walk rubric call and the reviewer memo. Both are cached or stubbed depending on mode."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from pydantic import BaseModel

from esgx import llm
from esgx.measures import talkwalk as _tw
from pipeline.spec import AgentSpec, Mode
from pipeline.tools.base import tool

REVIEW_PROMPT = """You are reviewing LLM-produced talk/walk scores for one firm and fiscal year.
Inputs: per-section sub-scores and summaries, and HARD DATA (self-reported scope 1+2, revenue; assurance flags where present).
Write a short auditor memo (max 150 words): (1) does the evidence support the walk score, (2) any contradiction
between the text and the hard data, (3) missing baselines, scopes or dates in the commitments. Then list
flags as short bullet strings. Do not invent numbers; cite sections by name."""


class ReviewMemo(BaseModel):
    memo: str
    flags: list[str]


@tool(kind="llm", cost="paid")
def llm_client(mode: Mode, agent: AgentSpec) -> Any:
    """Scoring client for the mode: DryRunClient (heuristics), CacheOnlyClient (cache, skip on miss) or the live client (Kimi or Claude by model id, paid)."""
    if mode == "dry_run":
        return _tw.DryRunClient()
    if mode == "cache_only":
        return _tw.CacheOnlyClient(model=agent.model)
    return _tw.make_client(model=agent.model, effort=agent.effort)


@tool(kind="llm", cost="paid")
def llm_score_section(client: Any, firm_name: str, row: pd.Series, hard_data: dict, max_chars: int = 60_000,
                      system: str = _tw.SYSTEM_PROMPT, talk_weights: dict | None = None, walk_weights: dict | None = None) -> dict:
    """Score one document section on the versioned talk/walk rubric (structured output, cached per prompt variant)."""
    return _tw.score_document(client, firm_name, row, hard_data, max_chars=max_chars, system=system,
                              talk_weights=talk_weights, walk_weights=walk_weights)


@tool(kind="llm", cost="paid")
def llm_review_memo(mode: Mode, agent: AgentSpec, firm: str, year: int, sections: pd.DataFrame, hard_data: dict) -> dict:
    """Auditor memo + flags for one firm-year from its scored sections and hard data; canned memo unless mode is live."""
    cols = [c for c in ("section", "form", "talk", "walk", "gap", "n_commitments", "n_quantified", "summary") if c in sections]
    payload = {"firm": firm, "year": year, "hard_data": hard_data, "sections": json.loads(sections[cols].to_json(orient="records"))}
    if mode != "live":
        gap = float(sections["gap"].mean()) if "gap" in sections else 0.0
        flags = ["talk exceeds walk by more than 2 points" if gap > 2 else "gap within 2 points"]
        if any(k.endswith("_change_pct") and (v or 0) > 0 for k, v in hard_data.items()):
            flags.append("emissions rising while text discusses reductions")
        return {"memo": f"[{mode}] {len(sections)} sections reviewed; mean gap {gap:.2f}.", "flags": flags, "model": mode}
    system = REVIEW_PROMPT + (f"\n\n{agent.role_prompt}" if agent.role_prompt.strip() else "")
    parsed, _ = llm.parse(agent.model, system, json.dumps(payload, default=str), ReviewMemo, effort=agent.effort, max_tokens=4000)
    return {"memo": parsed.memo, "flags": parsed.flags, "model": agent.model}


@tool(kind="compute", cost="free")
def rubric_system_prompt(role_prompt: str = "", agent_name: str = "agent") -> str:
    """The versioned base rubric, optionally followed by an agent's extra instructions (a prompt variant)."""
    extra = f"\n\nAdditional instructions from the {agent_name} agent:\n{role_prompt}" if role_prompt.strip() else ""
    return _tw.SYSTEM_PROMPT + extra
