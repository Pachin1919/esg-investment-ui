"""Score-ready document rows for the LLM talk/walk rubric from HKEX reports (Hong Kong and
HKEX-listed mainland China firms).

The streaming ingest keeps only per-report key figures and KPI pages; the talk/walk rubric
needs the narrative. So the picked report per firm-year (standalone ESG report when there is
one, else the annual report — `hk_stream.pick_reports`) is fetched, reusing the PDF cache under
data/raw/hkex, and its pages are joined into one text row per report. The rubric's cache key is
the report URL, so re-scores are free even though the joined text is not stored.
"""

from __future__ import annotations

import pandas as pd

from esgx.config import PROCESSED_DIR
from esgx.ingest import hkexnews as hx
from esgx.ingest.hk_stream import pick_reports

DOC_COLS = ["firm_id", "form", "filing_date", "period", "accession", "section", "text", "title", "fiscal_year"]


def row_for_report(firm_id: str, rep: dict) -> dict:
    """One score-ready row: the report's full text, keyed by its URL (the rubric cache key)."""
    path = hx.fetch_pdf(int(rep["stock_code"]), rep["url"])
    text = "\n\n".join(hx.pdf_pages(path))
    fy = int(rep["fiscal_year"])
    return {"firm_id": firm_id, "form": rep["doc_type"], "filing_date": rep["filing_date"], "period": f"{fy}-12-31",
            "accession": str(rep["url"]), "section": "full_report", "text": text, "title": rep["title"], "fiscal_year": fy}


def report_documents(firm_id: str, stock_code: int, stock_id: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Picked reports of one firm from a live HKEXnews listing, as score-ready rows."""
    reports = pd.DataFrame(hx.list_reports(stock_id, start=start))
    if reports.empty:
        return pd.DataFrame(columns=DOC_COLS)
    reports["firm_id"] = firm_id
    rows = [row_for_report(firm_id, r) for r in pick_reports(reports).to_dict("records")]
    return pd.DataFrame(rows, columns=DOC_COLS)


def stored_reports(firm_ids: list[str] | None = None) -> pd.DataFrame:
    """The report index written by the streaming ingest (data/processed/hk_reports.parquet),
    picked to one report per firm-year, without a new HKEXnews listing."""
    p = PROCESSED_DIR / "hk_reports.parquet"
    if not p.exists():
        raise SystemExit("no data/processed/hk_reports.parquet — run scripts/ingest_hk_stream.py first, or pass --tickers")
    reports = pd.read_parquet(p)
    if firm_ids:
        reports = reports[reports["firm_id"].isin(firm_ids)]
    return pick_reports(reports)
