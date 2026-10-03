"""The `sources` table: one row per place where a firm's text lives.

Source types and what they may feed:
* annual_report, interim_report, quarterly_report, esg_report – exchange archive, dated by filing.
* about_page – the firm describing itself: TALK only (Giannetti et al. 2023). Dated by retrieval,
  so it must not be used for earlier periods.
* news – third-party coverage: TALK / salience only (Engle et al. 2020; Gourier & Mathurin 2025).
  Dated by publication; never enters the walk pillar.
"""

from __future__ import annotations

import pandas as pd

SOURCE_COLS = ["firm_id", "source_type", "title", "url", "date", "language", "publisher", "found_by", "relevance", "note"]
REPORT_TYPES = ("annual_report", "interim_report", "quarterly_report", "esg_report")
TALK_ONLY_TYPES = ("about_page", "news")


def sources_frame(rows: list[dict]) -> pd.DataFrame:
    """Rows -> table with every column present, de-duplicated on (firm_id, url)."""
    df = pd.DataFrame(rows, columns=SOURCE_COLS) if rows else pd.DataFrame(columns=SOURCE_COLS)
    return df.drop_duplicates(["firm_id", "url"]).reset_index(drop=True)
