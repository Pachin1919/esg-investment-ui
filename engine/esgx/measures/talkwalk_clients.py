"""Scoring clients for the talk/walk rubric: real (Claude, structured output), dry-run (heuristics), cache-only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from esgx.measures.talkwalk_schema import TalkScores, TalkWalkScore, WalkScores

DEFAULT_MODEL = "claude-opus-5"


class ScoreClient(Protocol):
    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]: ...


@dataclass
class ClaudeClient:
    """Thin wrapper around anthropic.Anthropic().messages.parse with structured output."""

    model: str = DEFAULT_MODEL
    effort: str = "medium"
    max_tokens: int = 8000

    def __post_init__(self):
        from esgx.config import anthropic_client

        self._client = anthropic_client()

    def score(self, system: str, user: str) -> tuple[TalkWalkScore, dict]:
        resp = self._client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort},
            output_format=TalkWalkScore,
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {resp.stop_details}")
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
                 "cache_read": getattr(resp.usage, "cache_read_input_tokens", 0), "model": self.model}
        return resp.parsed_output, usage


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


