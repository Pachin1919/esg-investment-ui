"""Pipeline spec models shared by tools, agents, the orchestrator and the API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from esgx.llm import PRIMARY_MODEL as DEFAULT_MODEL

Mode = Literal["dry_run", "cache_only", "live"]
StageKind = Literal[
    "find_reports", "find_about_page", "find_news",
    "collect_documents", "collect_hard_data", "preprocess", "score_talkwalk",
    "dictionary_measures", "review", "aggregate",
]


class AgentSpec(BaseModel):
    """Runtime settings of an LLM agent for one stage. The agent's *definition* (role, allowed tools)
    lives in `pipeline/agents/<name>/agent.py`; this is what the user may change per run."""

    name: str = "agent"
    model: str = DEFAULT_MODEL
    effort: str = "medium"
    role_prompt: str = Field("", description="Extra instructions appended to the stage's base prompt")


class StageSpec(BaseModel):
    id: str
    kind: StageKind
    name: str
    description: str = ""
    enabled: bool = True
    agent: AgentSpec | None = Field(None, description="Set for LLM stages; None = deterministic code")
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineSpec(BaseModel):
    name: str = "default"
    version: str = "1"
    description: str = ""
    universe: Literal["hk", "tw"] = "hk"
    forms: list[str] = ["annual_report", "esg_report"]  # HKEX document types
    start: str = "2022-01-01"
    stages: list[StageSpec]
