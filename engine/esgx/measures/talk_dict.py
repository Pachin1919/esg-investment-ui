"""Deterministic talk score: intensity of green claim words in what a firm files (no LLM).

Giannetti, Jasova, Loumioti & Mendicino (2023) measure environmental talk as the share of
environmental-dictionary words in all of a bank's reports and call the top quintile "high
environmental reporters". Their robustness test (Sec. 4.3, App. B.2) drops hits that sit within
10 words of risk vocabulary, because describing climate risk is not a green claim. Here:

1. pool the text a firm filed for a fiscal year (full 10-K, optionally 8-K press releases),
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

from esgx.ingest import edgar_text as et
from esgx.measures import text_measures as tm
from esgx.measures.walk_hard import pct_score

COMMODITY_TERMS = {"oil", "gas", "coal", "diesel", "fracking", "nuclear", "hydro", "water", "wastewater", "waste",
                   "hazard", "spill", "toxic", "pollut", "wind", "solar", "forest"}
CLAIM_TERMS = [t for t in tm.ENV_TERMS if t not in COMMODITY_TERMS]
# Giannetti et al. (2023) Appendix B.2, as stems
RISK_STEMS = ("risk", "threat", "hazard", "danger", "challeng", "concern", "cost", "disrupt", "exposure", "regulat",
              "legislat", "impact", "monitor", "overse", "control", "scenario", "stress")
RISK_WINDOW = 10

_CLAIM_RE = re.compile("|".join(re.escape(t) for t in CLAIM_TERMS), re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")


def count_text(text: str) -> dict[str, int]:
    """n_words (stop words removed), n_green (all ENV_TERMS), n_claim_all (claim dictionary) and
    n_claim (claim hits with no risk stem within RISK_WINDOW non-stop words on either side)."""
    words, starts = [], []
    for m in _WORD_RE.finditer(text):
        w = m.group().lower()
        if w not in tm._STOP:
            words.append(w)
            starts.append(m.start())
    is_risk = np.fromiter((w.startswith(RISK_STEMS) for w in words), dtype=bool, count=len(words))
    risk_cum = np.concatenate([[0], np.cumsum(is_risk)])
    n_all = n_claim = 0
    for m in _CLAIM_RE.finditer(text):
        n_all += 1
        i = max(0, bisect_right(starts, m.start()) - 1)
        lo, hi = max(0, i - RISK_WINDOW), min(len(words), i + RISK_WINDOW + 1)
        if risk_cum[hi] - risk_cum[lo] == 0:
            n_claim += 1
    return {"n_words": len(words), "n_green": len(tm._ENV_RE.findall(text)), "n_claim_all": n_all, "n_claim": n_claim}


def filing_counts(firm_id: str, cik: int, forms: tuple[str, ...] = ("10-K",), start: str = "2019-01-01", max_8k: int = 20) -> pd.DataFrame:
    """One row per document with counts over its whole text (HTML cached under data/raw/edgar).
    10-K: the primary document. 8-K: attached press releases (voluntary communication), newest first."""
    rows, n8k = [], 0
    for f in et.list_filings(cik, forms, start):
        if f.form == "8-K":
            if n8k >= max_8k:
                continue
            docs = et.press_release_docs(f.cik, f.acc_nodash, f.accession)
            n8k += bool(docs)
        else:
            docs = [f.primary_doc]
        year = pd.to_datetime(f.report_date or f.filing_date).year
        for doc in docs:
            text = et.html_to_text(et.fetch_document(f.cik, f.acc_nodash, doc))
            rows.append({"firm_id": firm_id, "year": year, "form": f.form, "filing_date": f.filing_date, "accession": f.accession, "doc": doc, **count_text(text)})
    return pd.DataFrame(rows)


def report_counts(docs: pd.DataFrame) -> pd.DataFrame:
    """One row per HKEX report (`documents_hk` rows with a local PDF) with counts over all its pages.
    ESG / sustainability reports are voluntary communication, the document type Giannetti et al. use;
    annual reports are pooled with them per fiscal year."""
    from pathlib import Path

    from esgx.ingest.hkexnews import pdf_pages

    rows = []
    for d in docs[docs["path"].notna()].itertuples():
        text = "\n".join(pdf_pages(Path(d.path)))
        rows.append({"firm_id": d.firm_id, "year": int(d.fiscal_year), "form": d.doc_type, "filing_date": d.filing_date,
                     "accession": Path(d.path).stem, "doc": Path(d.path).name, **count_text(text)})
    return pd.DataFrame(rows)


def firm_year_intensity(counts: pd.DataFrame) -> pd.DataFrame:
    """Pool documents to firm × year: summed counts and hits per 1 000 words."""
    c = counts[counts["n_words"] > 0]
    out = c.groupby(["firm_id", "year"]).agg(n_docs=("accession", "nunique"), n_words=("n_words", "sum"), n_green=("n_green", "sum"),
                                              n_claim_all=("n_claim_all", "sum"), n_claim=("n_claim", "sum")).reset_index()
    out["claim_per_1000"] = 1000.0 * out["n_claim"] / out["n_words"]
    out["green_per_1000"] = 1000.0 * out["n_green"] / out["n_words"]
    out["risk_context_share"] = 1.0 - out["n_claim"] / out["n_claim_all"].where(out["n_claim_all"] > 0)
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

def collect_us_counts(firms: pd.DataFrame, scored_ids: set[str], tickers: list[str], sectors: list[str], forms: tuple[str, ...], start: str, max_8k: int) -> pd.DataFrame:
    """Download (cached) and count EDGAR filings for the given tickers and sectors.
    
    Only firms that already have a walk score (scored_ids) are fetched when matching by sector,
    so no downloads are wasted. Results are cached in data/processed/det_counts_*.csv.
    """
    from esgx.config import PROCESSED_DIR
    from tqdm import tqdm
    
    sel = firms[firms["firm_id"].isin(tickers) | (firms["sector"].isin(sectors) & firms["firm_id"].isin(scored_ids))]
    if sel.empty:
        raise RuntimeError("No firms selected: pass tickers and/or sectors")
    
    cache = PROCESSED_DIR / f"det_counts_{'_'.join(sorted(forms))}.csv"
    done = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["firm_id"])
    frames = [done]
    todo = sel[~sel["firm_id"].isin(done["firm_id"])]
    for r in tqdm(todo.itertuples(), total=len(todo)):
        try:
            frames.append(filing_counts(r.firm_id, int(r.cik), forms=forms, start=start, max_8k=max_8k))
        except Exception as e:  # noqa: BLE001
            print(f"skip {r.firm_id}: {type(e).__name__}: {e}")
        pd.concat(frames, ignore_index=True).to_csv(cache, index=False)
    return pd.concat(frames, ignore_index=True)
