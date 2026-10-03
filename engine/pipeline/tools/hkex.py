"""HKEXnews tools: annual / ESG report index, PDF download, page text."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esgx.ingest import hkexnews as _h
from pipeline.tools.base import tool


@tool(kind="scrape", cost="network")
def hkex_list_reports(stock_id: int, start: str = "2020-01-01") -> list[dict]:
    """List annual and ESG reports for an HKEX stock id from the HKEXnews title search."""
    return _h.list_reports(stock_id, start=start)


@tool(kind="scrape", cost="network")
def hkex_fetch_pdf(stock_code: int, url: str) -> Path:
    """Download (or reuse the cached) report PDF under data/raw/hkex/<code>/."""
    return _h.fetch_pdf(stock_code, url)


@tool(kind="compute", cost="free")
def hkex_pdf_pages(path: Path) -> list[str]:
    """Extract text per page from a report PDF."""
    return _h.pdf_pages(path)


@tool(kind="scrape", cost="network")
def hkex_load_documents(firm_id: str, stock_code: int, stock_id: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Documents table for one HK firm (annual + ESG reports with page counts and local paths)."""
    return _h.load_documents_hk(firm_id, stock_code, stock_id, start=start)


@tool(kind="scrape", cost="network")
def hkex_report_documents(firm_id: str, stock_code: int, stock_id: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Score-ready rows for the talk/walk rubric: the picked report per firm-year as full text, keyed by URL."""
    from esgx.ingest.hk_documents import report_documents

    return report_documents(firm_id, stock_code, stock_id, start=start)
