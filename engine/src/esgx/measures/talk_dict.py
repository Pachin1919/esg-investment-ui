"""Deterministic talk score: intensity of green claim words in what a firm files (no LLM).

Giannetti, Jasova, Loumioti & Mendicino (2023) measure environmental talk as the share of
environmental-dictionary words in all of a bank's reports and call the top quintile "high
environmental reporters". Their robustness test (Sec. 4.3, App. B.2) drops hits that sit within
10 words of risk vocabulary, because describing climate risk is not a green claim. Here:

1. pool the documents a firm filed for a fiscal year (HKEX annual and ESG reports);
   only per-document key figures are stored (`measures.text_metrics`), not the documents,
2. count hits of the claim dictionary and words (stop words removed),
3. drop hits in risk context (Giannetti's B.2 list) -> ``n_claim``,
4. intensity = claim hits per 1 000 words (a share, so report length does not matter),
5. talk = 0-10 from the percentile rank of intensity within industry and year (10 = talks most).

Adaptation: Giannetti's dictionary is bank-specific and includes fuels ("oil", "coal"), which for
a bank signal environmental topics but for an energy or utility firm are the product. The claim
dictionary is therefore `ENV_TERMS` minus fuel, commodity and operational-hazard terms.
The unfiltered count (`n_green`, all ENV_TERMS, any context) is kept next to it for comparison.
"""

from __future__ import annotations

import re
from bisect import bisect_right

import numpy as np
import pandas as pd

from esgx.measures import text_measures as tm
from esgx.measures.walk_hard import pct_score

COMMODITY_TERMS = {"oil", "gas", "coal", "diesel", "fracking", "nuclear", "hydro", "water", "wastewater", "waste",
                   "hazard", "spill", "toxic", "pollut", "wind", "solar", "forest"}
CLAIM_TERMS = [t for t in tm.ENV_TERMS if t not in COMMODITY_TERMS]
# Giannetti et al. (2023) Appendix B.2, as stems
RISK_STEMS = ("risk", "threat", "hazard", "danger", "challeng", "concern", "cost", "disrupt", "exposure", "regulat",
              "legislat", "impact", "monitor", "overse", "control", "scenario", "stress")
RISK_WINDOW = 10

# word-start boundary (so "oil" does not hit "soil"), longest term first (so "carbon capture" beats "carbon")
_TERM_RE = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in sorted(tm.ENV_TERMS, key=len, reverse=True)) + ")", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")


def term_counts(text: str) -> tuple[int, dict[str, list[int]]]:
    """(n_words without stop words, {term: [hits, hits with no risk stem within RISK_WINDOW words]})
    for every ENV_TERMS term that occurs. Per-term counts are what gets stored, so a narrower or
    re-weighted dictionary can be recomputed later without the document."""
    words, starts = [], []
    for m in _WORD_RE.finditer(text):
        w = m.group().lower()
        if w not in tm._STOP:
            words.append(w)
            starts.append(m.start())
    is_risk = np.fromiter((w.startswith(RISK_STEMS) for w in words), dtype=bool, count=len(words))
    risk_cum = np.concatenate([[0], np.cumsum(is_risk)])
    terms: dict[str, list[int]] = {}
    for m in _TERM_RE.finditer(text):
        c = terms.setdefault(m.group().lower(), [0, 0])
        c[0] += 1
        i = max(0, bisect_right(starts, m.start()) - 1)
        lo, hi = max(0, i - RISK_WINDOW), min(len(words), i + RISK_WINDOW + 1)
        if risk_cum[hi] - risk_cum[lo] == 0:
            c[1] += 1
    return len(words), terms


def counts_from_terms(n_words: int, terms: dict[str, list[int]], claim_terms: list[str] | None = None) -> dict[str, int]:
    """n_words, n_green (all terms), n_claim_all (claim dictionary) and n_claim (claim hits outside risk context)."""
    claim = set(claim_terms or CLAIM_TERMS)
    return {"n_words": n_words, "n_green": sum(c[0] for c in terms.values()),
            "n_claim_all": sum(c[0] for t, c in terms.items() if t in claim),
            "n_claim": sum(c[1] for t, c in terms.items() if t in claim)}


def count_text(text: str) -> dict[str, int]:
    return counts_from_terms(*term_counts(text))


def firm_year_intensity(counts: pd.DataFrame) -> pd.DataFrame:
    """Pool documents to firm × year: summed counts and hits per 1 000 words."""
    c = counts[counts["n_words"] > 0]
    out = c.groupby(["firm_id", "year"]).agg(n_docs=("accession", "nunique"), n_words=("n_words", "sum"), n_green=("n_green", "sum"),
                                              n_claim_all=("n_claim_all", "sum"), n_claim=("n_claim", "sum")).reset_index()
    out["claim_per_1000"] = 1000.0 * out["n_claim"] / out["n_words"]
    out["green_per_1000"] = 1000.0 * out["n_green"] / out["n_words"]
    out["risk_context_share"] = 1.0 - out["n_claim"] / out["n_claim_all"].where(out["n_claim_all"] > 0)
    for col in ("env_sentiment", "forward_looking_share", "glossiness"):  # word-weighted, when the metrics carry them
        if col in c.columns:
            w = c.assign(_x=c[col] * c["n_words"]).groupby(["firm_id", "year"])["_x"].sum().to_numpy()
            out[col] = w / out["n_words"]
    return out


def talk_score(intensity: pd.DataFrame, firms: pd.DataFrame, industry_col: str = "sector", min_group: int = 5) -> pd.DataFrame:
    """Add `talk` (0-10, percentile of claim intensity within industry × year; industries with fewer
    than `min_group` firms that year are ranked across the whole year), `talk_universe` (percentile
    across all firms that year, Giannetti's cross-section) and `talk_unfiltered` (all ENV_TERMS,
    any context: the measure before the commodity and risk adjustments)."""
    df = intensity.merge(firms[["firm_id", industry_col]].drop_duplicates("firm_id"), on="firm_id", how="left")
    size = df.groupby(["year", industry_col])["firm_id"].transform("count")
    df["rank_group"] = np.where(size >= min_group, df[industry_col], "_all")
    grp = [df["year"], df["rank_group"]]
    df["talk"] = pct_score(df["claim_per_1000"], grp, lower_is_greener=False)
    df["talk_universe"] = pct_score(df["claim_per_1000"], [df["year"]], lower_is_greener=False)
    df["talk_unfiltered"] = pct_score(df["green_per_1000"], grp, lower_is_greener=False)
    return df
