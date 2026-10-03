"""Cheap, deterministic text measures that complement the LLM rubric (no API needed).

* env_keyword_share   – Giannetti et al. 2023: environment-keyword count / non-stopword count,
                        using a non-directional dictionary (no 'environmental', 'sustainability').
* env_sentiment       – LM-style sentiment in a ±10-word window around each environment keyword.
* forward_looking_share – share of environment-keyword hits that sit within 10 words of a
                        forward-looking term ('commit', 'plan', 'target', 'will', 'aim', ...).
* climate_similarity  – Engle et al. 2020: cosine similarity between the document's term
                        frequencies and a fixed climate vocabulary.
* glossiness          – two-stage combination of the two above: a cosine gate keeps only the
                        climate-relevant segments (Engle et al. 2020 vocabulary, low threshold as in
                        Gourier & Mathurin 2025), then LM sentiment around environment terms is computed
                        on those segments only (Giannetti et al. 2023). glossiness = climate_share x
                        max(gated_sentiment, 0). A TALK measure: much climate content, positive tone.
                        It must never enter the walk pillar.

Drop the full Loughran–McDonald word lists into data/dictionaries/{lm_positive,lm_negative}.txt
to replace the compact built-in lists.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache

from esgx.config import DATA_DIR

# Non-directional environment terms (subset of Giannetti et al. Appendix B.1, stems)
ENV_TERMS = [
    "carbon", "co2", "ghg", "greenhouse", "emission", "methane", "coal", "oil", "gas", "diesel", "fracking",
    "renewable", "solar", "wind", "photovoltaic", "hydro", "geothermal", "biofuel", "biodiesel", "nuclear",
    "recycl", "waste", "wastewater", "water", "pollut", "toxic", "hazard", "spill", "biodivers", "forest",
    "deforest", "reforest", "ecosystem", "air quality", "climate", "decarbon", "net zero", "net-zero",
    "electric vehicle", "ev charging", "energy efficien", "leed", "carbon capture", "ccs", "hydrogen",
    "scope 1", "scope 2", "scope 3", "sbti", "science based target", "tcfd", "csrd", "cbam", "carbon tax",
    "cap-and-trade", "emissions trading", "paris agreement", "energy transition", "low-carbon", "low carbon",
]
FORWARD_TERMS = ["commit", "plan", "target", "future", "will", "aim", "aspire", "goal", "intend", "expect", "by 2030", "by 2040", "by 2050", "ambition", "pledge"]
REALISED_TERMS = ["reduced", "achieved", "decreased", "cut", "installed", "invested", "completed", "delivered", "verified", "assured", "audited", "since 20", "compared with 20", "versus 20"]

_POS = ["achieve", "improve", "benefit", "success", "strong", "progress", "positive", "leader", "leading", "opportunit", "gain", "enhance", "excellent", "efficient", "innovat", "advantage", "best"]
_NEG = ["loss", "risk", "adverse", "fail", "decline", "penalt", "violat", "litigation", "impair", "negative", "unable", "weak", "difficult", "concern", "uncertain", "liabilit", "fine", "lawsuit"]
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "by", "as", "at", "is", "are", "was", "were", "be", "been", "from", "that", "this", "it", "its", "we", "our", "their", "they", "which", "will", "may"}


@lru_cache(maxsize=1)
def _lm_lists() -> tuple[list[str], list[str]]:
    d = DATA_DIR / "dictionaries"
    pos, neg = _POS, _NEG
    if (d / "lm_positive.txt").exists():
        pos = [w.strip().lower() for w in (d / "lm_positive.txt").read_text().splitlines() if w.strip()]
    if (d / "lm_negative.txt").exists():
        neg = [w.strip().lower() for w in (d / "lm_negative.txt").read_text().splitlines() if w.strip()]
    return pos, neg


_ENV_RE = re.compile("|".join(re.escape(t) for t in ENV_TERMS), re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z][a-z\-]+")


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP]


def env_keyword_share(text: str) -> float:
    toks = _tokens(text)
    if not toks:
        return 0.0
    return len(_ENV_RE.findall(text)) / len(toks)


def _window_stats(text: str, window: int = 10) -> tuple[float, float, int]:
    """(sentiment, forward_share, n_hits): sentiment per Giannetti = sum over env hits of (pos-neg) in ±window words, / n_hits."""
    words = text.lower().split()
    pos, neg = _lm_lists()
    hits = [i for i, w in enumerate(words) if _ENV_RE.search(w)]
    if not hits:
        return 0.0, 0.0, 0
    sent, fwd = 0.0, 0
    for i in hits:
        ctx = " ".join(words[max(0, i - window): i + window + 1])
        sent += sum(ctx.count(p) for p in pos) - sum(ctx.count(n) for n in neg)
        if any(f in ctx for f in FORWARD_TERMS):
            fwd += 1
    return sent / len(hits), fwd / len(hits), len(hits)


def env_sentiment(text: str) -> float:
    return _window_stats(text)[0]


def forward_looking_share(text: str) -> float:
    return _window_stats(text)[1]


def realised_share(text: str, window: int = 10) -> float:
    """Share of env hits within ±window words of realised/past-action terms."""
    words = text.lower().split()
    hits = [i for i, w in enumerate(words) if _ENV_RE.search(w)]
    if not hits:
        return 0.0
    n = 0
    for i in hits:
        ctx = " ".join(words[max(0, i - window): i + window + 1])
        if any(r in ctx for r in REALISED_TERMS):
            n += 1
    return n / len(hits)


def climate_similarity(text: str, vocab: dict[str, float] | None = None) -> float:
    """Cosine similarity between document term counts and a climate vocabulary (Engle et al. style).
    Default vocabulary = ENV_TERMS with equal weight; pass tf-idf weights from an authoritative corpus to refine."""
    vocab = vocab or {t: 1.0 for t in ENV_TERMS}
    counts = Counter(_tokens(text))
    dot = sum(counts.get(t, 0) * w for t, w in vocab.items())
    nd = math.sqrt(sum(c * c for c in counts.values()))
    nv = math.sqrt(sum(w * w for w in vocab.values()))
    return dot / (nd * nv) if nd and nv else 0.0


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _segments(text: str, min_chars: int = 20) -> list[str]:
    """Paragraphs (blank-line separated) if there are at least two, otherwise sentences."""
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= min_chars]
    if len(paras) >= 2:
        return paras
    return [s.strip() for s in _SENT_SPLIT_RE.split(text) if len(s.strip()) >= min_chars]


def glossiness(
    text: str,
    threshold: float = 0.01,
    window: int = 10,
    vocab: dict[str, float] | None = None,
) -> dict[str, float]:
    """Glossy-talk measure: cosine gate (Engle et al. 2020) then LM sentiment (Giannetti et al. 2023).

    Stage 1 – topic gate. The document is split into segments (paragraphs, or sentences when the
    text has no paragraph breaks). A segment is climate-relevant if its cosine similarity to the
    climate vocabulary exceeds `threshold`. The threshold is deliberately low so relevant segments
    are rarely dropped (Gourier & Mathurin 2025 apply the same rule to WSJ articles).
    Stage 2 – tone. Net Loughran–McDonald sentiment in a ±`window`-word context around every
    environment term, averaged per hit, computed on the gated segments only (Giannetti et al. 2023,
    following Hassan et al. 2019).

    Returns
    -------
    climate_share    share of segments passing the gate (how much of the text is about climate)
    gated_sentiment  mean net sentiment per environment hit inside the gated segments
    glossiness       climate_share * max(gated_sentiment, 0): much climate content with a positive
                     tone. High = "glossy". This is TALK; it says nothing about actions.
    """
    segs = _segments(text)
    if not segs:
        return {"climate_share": 0.0, "gated_sentiment": 0.0, "glossiness": 0.0}
    kept = [s for s in segs if climate_similarity(s, vocab) > threshold]
    share = len(kept) / len(segs)
    sent = _window_stats(" ".join(kept), window)[0] if kept else 0.0
    return {"climate_share": share, "gated_sentiment": sent, "glossiness": share * max(sent, 0.0)}


def text_measures(text: str) -> dict[str, float]:
    sent, fwd, n = _window_stats(text)
    out = {
        "env_keyword_share": env_keyword_share(text),
        "env_sentiment": sent,
        "forward_looking_share": fwd,
        "realised_share": realised_share(text),
        "climate_similarity": climate_similarity(text),
        "n_env_hits": n,
    }
    out.update(glossiness(text))
    return out
