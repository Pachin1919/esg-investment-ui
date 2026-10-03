"""Agent registry. One sub-package per agent: `pipeline/agents/<id>/agent.py` defines `AGENT`
(an `AgentDefinition`); `brain/teknik/pipeline/agents/Agent <id>.md` explains it in words. `AGENTS` preserves pipeline order:
the three source finders (off by default) come first, then the talk/walk chain."""

from pipeline.agents import (
    aggregate,
    collect_documents,
    collect_hard_data,
    dictionary_measures,
    find_about_page,
    find_news,
    find_reports,
    preprocess,
    review,
    score_talkwalk,
)
from pipeline.agents.base import AgentDefinition, StageTask

AGENTS: dict[str, AgentDefinition] = {
    a.AGENT.id: a.AGENT
    for a in (find_reports, find_about_page, find_news, collect_documents, collect_hard_data, preprocess, score_talkwalk, dictionary_measures, review, aggregate)
}

__all__ = ["AGENTS", "AgentDefinition", "StageTask"]


def catalogue() -> list[dict]:
    return [a.to_dict() for a in AGENTS.values()]
