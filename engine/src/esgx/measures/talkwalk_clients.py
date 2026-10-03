"""Scoring clients for the talk/walk rubric: live (Kimi or Claude via `esgx.llm`, structured output),
dry-run (heuristics), cache-only. `make_client` picks the live client from the model id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from esgx import llm
from esgx.measures.talkwalk_schema import TalkScores, TalkWalkScore, WalkScores

DEFAULT_MODEL = llm.PRIMARY_MODEL


class ScoreClient(Protocol):
    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]: ...


@dataclass
class LiveClient:
    """Paid structured-output call through `esgx.llm.parse` (Kimi or Claude, decided by the model id)."""

    model: str = DEFAULT_MODEL
    effort: str = "medium"
    max_tokens: int = 8000

    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]:
        return llm.parse(self.model, system, user, TalkWalkScore, effort=self.effort, max_tokens=self.max_tokens)


ClaudeClient = KimiClient = LiveClient  # one client for both providers; names kept for callers


def make_client(model: str = DEFAULT_MODEL, effort: str = "medium") -> LiveClient:
    return LiveClient(model=model, effort=effort)


class DryRunClient:
    """Deterministic stand-in for tests / no-API-key runs: scores from keyword heuristics."""

    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]:
        t = user.lower()
        fut = sum(t.count(k) for k in ["will", "aim", "target", "by 2030", "by 2050", "commit", "aspire"])
        past = sum(t.count(k) for k in ["reduced", "achieved", "invested", "verified", "assured", "decreased"])
        n = max(1, fut + past)
        talk = min(10.0, 10 * fut / n)
        walk = min(10.0, 10 * past / n)
        return TalkWalkScore(
            climate_relevance=min(10.0, t.count("climate") + t.count("emission")),
            talk=TalkScores(ambition=talk, specificity=5, forward_looking_share=talk, hedging=5, promotional_tone=talk),
            walk=WalkScores(realised_reductions=walk, capital_deployed=walk, verification=walk, governance=5, hard_data_consistency=5, implementation_share=walk),
            commitments=[], evidence_talk=[], evidence_walk=[], summary="dry run",
        ), {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "model": "dry-run"}


class CacheOnlyClient:
    """Never calls the API: `score_document` serves cached responses and marks misses as skipped
    (`skip_reason="cache_miss"`). Use it to rebuild the output tables (new dictionary columns,
    changed aggregation) at zero cost."""

    cache_only = True

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]:
        raise LookupError("cache miss in CacheOnlyClient")


