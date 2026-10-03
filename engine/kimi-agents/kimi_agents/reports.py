"""Report finder: annual, interim, quarterly and ESG reports of an SEHK-listed firm from HKEXnews.

No model and no search engine: the exchange archive is complete and every document carries its
filing date. Uses the HKEXnews title search (category 40000, "Financial Statements / ESG
Information"); the title decides the report type.
"""

from __future__ import annotations

import json
import re
import time

import pandas as pd
import requests

from esgx.ingest.hkexnews import BASE, SEARCH, fiscal_year_from_title

_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)"}
_QUARTERLY = re.compile(r"\bquarterly\b|\b(first|third)[- ]quarter", re.IGNORECASE)
_INTERIM = re.compile(r"\binterim\b|half-year", re.IGNORECASE)
_ANNUAL = re.compile(r"\bannual report\b", re.IGNORECASE)
_ESG = re.compile(r"\b(esg|environmental, social|sustainab|climate)", re.IGNORECASE)


def report_type(title: str) -> str | None:
    """'quarterly_report' | 'interim_report' | 'annual_report' | 'esg_report' | None."""
    if _QUARTERLY.search(title):
        return "quarterly_report"
    if _INTERIM.search(title):
        return "interim_report"
    if _ANNUAL.search(title):
        return "annual_report"
    return "esg_report" if _ESG.search(title) else None


def search_titles(stock_id: int, start: str, end: str | None = None) -> list[dict]:
    """Raw rows of the HKEXnews title search for one HKEX stock id."""
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    params = {"sortDir": 0, "sortByOptions": "DateTime", "category": 0, "market": "SEHK", "stockId": int(stock_id), "documentType": -1,
              "fromDate": pd.Timestamp(start).strftime("%Y%m%d"), "toDate": pd.Timestamp(end).strftime("%Y%m%d"), "title": "",
              "searchType": 1, "t1code": 40000, "t2Gcode": -2, "t2code": -2, "rowRange": 200, "lang": "E"}
    r = requests.get(SEARCH, params=params, headers=_HEADERS, timeout=60)
    r.raise_for_status()
    time.sleep(0.5)
    return json.loads(r.json().get("result", "[]"))


def run(firm_id: str, stock_id: int, start: str = "2023-01-01", rows: list[dict] | None = None) -> list[dict]:
    """`sources` rows for one firm. `rows` lets tests pass title-search rows instead of calling HKEXnews."""
    out = []
    for row in rows if rows is not None else search_titles(stock_id, start):
        kind = report_type(row["TITLE"])
        if kind is None or row.get("FILE_TYPE", "PDF").upper() != "PDF":
            continue
        date = pd.to_datetime(row["DATE_TIME"], dayfirst=True).strftime("%Y-%m-%d")
        out.append({"firm_id": firm_id, "source_type": kind, "title": row["TITLE"], "url": BASE + row["FILE_LINK"], "date": date,
                    "language": "English", "publisher": "HKEXnews", "found_by": "reports", "relevance": 1.0,
                    "note": f"FY{fiscal_year_from_title(row['TITLE'], date)}"})
    return out
