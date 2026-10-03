"""Source catalogue: where a firm's text lives (reports, about page, news), one row per source.

The `sources` table (schema.py) only records *where* a document is and *when* it was published.
Reading and scoring happens downstream. Source types and the pillar they may feed:

* annual_report, interim_report, quarterly_report, esg_report – from the exchange archive
  (HKEXnews), never from a web search: the archive is complete and dated.
* about_page – the firm's own description of itself. Talk only (Giannetti et al. 2023: disclosure
  tone is what a firm says, not what it does).
* news – third-party coverage with a publication date. Talk / salience only (Engle et al. 2020;
  Gourier & Mathurin 2025). Never enters the walk pillar; the date guards against look-ahead.
"""

from __future__ import annotations

import pandas as pd

from esgx.ingest import hkexnews
from esgx.schema import validate

SOURCE_COLS = ["firm_id", "source_type", "title", "url", "date", "language", "publisher", "found_by", "relevance", "note"]
REPORT_TYPES = ("annual_report", "interim_report", "quarterly_report", "esg_report")
TALK_ONLY_TYPES = ("about_page", "news")


def sources_frame(rows: list[dict]) -> pd.DataFrame:
    """Rows -> validated `sources` table with every column present, de-duplicated on (firm_id, url)."""
    df = pd.DataFrame(rows, columns=SOURCE_COLS) if rows else pd.DataFrame(columns=SOURCE_COLS)
    return validate(df.drop_duplicates(["firm_id", "url"]).reset_index(drop=True), "sources")


def report_sources_hk(firm_id: str, stock_id: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Annual, interim, quarterly and ESG reports of one SEHK firm from the HKEXnews title search."""
    rows = [
        {"firm_id": firm_id, "source_type": r["doc_type"], "title": r["title"], "url": r["url"], "date": r["filing_date"],
         "language": "English", "publisher": "HKEXnews", "found_by": "find_reports", "relevance": 1.0, "note": f"FY{r['fiscal_year']}"}
        for r in hkexnews.list_reports(stock_id, start=start, kinds=hkexnews.ALL_KINDS)
    ]
    return sources_frame(rows)


def merge_sources(*frames: pd.DataFrame | None) -> pd.DataFrame:
    parts = [f for f in frames if f is not None and len(f)]
    return sources_frame(pd.concat(parts, ignore_index=True).to_dict("records")) if parts else sources_frame([])
