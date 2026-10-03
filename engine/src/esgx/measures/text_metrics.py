"""Per-document text key figures stored as JSON, so the documents themselves can be discarded.

One file per document under data/processed/text_metrics/<market>/<firm_id>/<doc_id>.json:

    {"meta":    {firm_id, year, form, filing_date, accession, ...},
     "version": METRICS_VERSION,
     "counts":  {n_words, n_green, n_claim_all, n_claim},
     "intensity": {claim_per_1000, green_per_1000, risk_context_share},
     "sentiment": {env_sentiment, forward_looking_share, realised_share, climate_similarity,
                   climate_share, gated_sentiment, glossiness, n_env_hits, env_keyword_share},
     "terms":   {term: [hits, hits outside risk context]}}

`terms` holds the count of every dictionary term that occurs, so the claim dictionary can be
narrowed or re-weighted later from the JSON alone (`talk_dict.counts_from_terms`). What cannot be
recomputed without the document: terms that are not in `text_measures.ENV_TERMS`, a different risk
window, and the sentiment measures. Bump METRICS_VERSION when any of those change; files of an older
version are then recomputed on the next run (which downloads the document again).

Sources of the measures: Giannetti et al. (2023) word share, sentiment window and risk-context
exclusion; Engle et al. (2020) vocabulary cosine; see `talk_dict` and `text_measures`.
Written by the HKEX streaming ingest (`ingest.hk_stream`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from esgx.config import PROCESSED_DIR
from esgx.measures import text_measures as tm
from esgx.measures.talk_dict import counts_from_terms, term_counts

METRICS_VERSION = "v1"
METRICS_DIR = PROCESSED_DIR / "text_metrics"


def document_metrics(text: str) -> dict:
    """All key figures of one document as a JSON-serialisable dict."""
    n_words, terms = term_counts(text)
    c = counts_from_terms(n_words, terms)
    per = 1000.0 / n_words if n_words else 0.0
    return {
        "version": METRICS_VERSION,
        "counts": c,
        "intensity": {"claim_per_1000": c["n_claim"] * per, "green_per_1000": c["n_green"] * per,
                      "risk_context_share": 1.0 - c["n_claim"] / c["n_claim_all"] if c["n_claim_all"] else None},
        "sentiment": {k: float(v) for k, v in tm.text_measures(text).items()},
        "terms": dict(sorted(terms.items(), key=lambda kv: -kv[1][0])),
    }


def metrics_path(market: str, firm_id: str, doc_id: str) -> Path:
    return METRICS_DIR / market / firm_id / (re.sub(r"[^A-Za-z0-9_.\-]", "_", doc_id) + ".json")


def write_metrics(market: str, meta: dict, metrics: dict) -> Path:
    p = metrics_path(market, meta["firm_id"], meta["accession"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"meta": meta, **metrics}, indent=1, default=str))
    return p


def is_current(path: Path) -> bool:
    return path.exists() and json.loads(path.read_text()).get("version") == METRICS_VERSION


def load_metrics(market: str) -> pd.DataFrame:
    """Flat table of all stored documents of a market: meta, counts, intensity and sentiment columns."""
    rows = []
    for p in sorted((METRICS_DIR / market).glob("*/*.json")):
        d = json.loads(p.read_text())
        rows.append({**d["meta"], **d["counts"], **d["intensity"], **d["sentiment"]})
    return pd.DataFrame(rows)
