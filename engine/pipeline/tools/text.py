"""Dictionary text tools (no API): keyword share, sentiment window, similarity, glossiness, climate filter."""

from __future__ import annotations

from esgx.ingest.text_filter import climate_passages as _climate_passages
from esgx.measures import text_measures as _tm
from pipeline.tools.base import tool


@tool(kind="compute", cost="free")
def text_measures(text: str) -> dict[str, float]:
    """All dictionary measures for one text: env_keyword_share, env_sentiment, forward/realised share, climate_similarity, glossiness."""
    return _tm.text_measures(text)


@tool(kind="compute", cost="free")
def glossiness(text: str, threshold: float = 0.01) -> dict[str, float]:
    """Cosine gate then LM sentiment: climate_share, gated_sentiment, glossiness (a talk measure)."""
    return _tm.glossiness(text, threshold=threshold)


@tool(kind="compute", cost="free")
def climate_passages(text: str, window: int = 1, max_chars: int = 60_000) -> tuple[str, float]:
    """Keep paragraphs mentioning climate terms (plus neighbours); returns (text, share of paragraphs kept)."""
    return _climate_passages(text, window=window, max_chars=max_chars)
