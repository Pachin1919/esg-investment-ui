"""Streaming ingest of HKEX reports: download one PDF, keep only what the measures need, delete it.

A report is 5-30 MB as PDF; the measures need two small things from it:

* text metrics : word counts, per-term dictionary hits and sentiment measures over the whole text,
                 written as one JSON file per report (`measures.text_metrics`)
* KPI pages    : the few pages that hold ESG figures, found by scoring every page on unit and
                 keyword patterns per category (GHG, energy, water, waste). Only these pages go to
                 the LLM extractor, so tokens are spent on tables with numbers, not on narrative.

Stores (data/processed, a few MB for the whole index):
  hk_reports.parquet    one row per report: metadata and n_pages (index of what has been processed)
  text_metrics/hk/      one JSON per report with the key figures
  hk_kpi_pages.parquet  one row per kept page and category: page number, score, text (capped)

HKEX ESG Reporting Guide (Appendix C2): A1.2 GHG scope 1 and 2, A2.1 energy, A2.2 water,
A1.3 / A1.4 hazardous and non-hazardous waste are the KPIs the patterns target.
"""

from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests

from esgx.ingest import emissions_hk as eh
from esgx.ingest import hkexnews as hx
from esgx.measures.text_metrics import document_metrics, write_metrics

PAGE_CHARS = 7000
TOP_K = 6
_NUM = r"\d[\d,\.]*\s*"
CATEGORY_PATTERNS: dict[str, list[tuple[int, re.Pattern]]] = {
    "ghg": [(3, eh._SCOPE_RE), (2, eh._UNIT_RE), (1, eh._GHG_RE)],  # same scoring as emissions_hk.candidate_pages
    "energy": [(3, re.compile(_NUM + r"(?:kwh|mwh|gwh|gj|tj|terajoules?|gigajoules?)\b", re.IGNORECASE)),
               (1, re.compile(r"energy consumption|electricity consumption|energy intensity|purchased electricity", re.IGNORECASE))],
    "water": [(3, re.compile(_NUM + r"(?:m3|m³|cubic met(?:re|er)s?|megalit(?:re|er)s?|ml\b)", re.IGNORECASE)),
              (1, re.compile(r"water consumption|water withdrawal|water intensity|water usage", re.IGNORECASE))],
    "waste": [(2, re.compile(r"hazardous waste|non-hazardous waste", re.IGNORECASE)),
              (1, re.compile(r"waste (?:generated|produced|disposed|recycled|diverted)", re.IGNORECASE))],
}
REPORT_COLS = ["firm_id", "stock_code", "doc_type", "filing_date", "fiscal_year", "title", "url", "size", "n_pages"]
PAGE_COLS = ["firm_id", "url", "doc_type", "fiscal_year", "category", "page", "score", "text"]


def kpi_pages(pages: list[str], top_k: int = TOP_K, max_chars: int = PAGE_CHARS) -> list[dict]:
    """Top-scoring pages per category (page numbers are 1-based), text capped at `max_chars`."""
    out = []
    for cat, patterns in CATEGORY_PATTERNS.items():
        scored = [(sum(w * len(rx.findall(p)) for w, rx in patterns), i) for i, p in enumerate(pages, start=1)]
        for score, i in sorted((s for s in scored if s[0] > 0), reverse=True)[:top_k]:
            out.append({"category": cat, "page": i, "score": score, "text": pages[i - 1][:max_chars]})
    return out


def _download(url: str, dest: Path, attempts: int = 4) -> None:
    """Streamed download, retried with a growing pause: HKEXnews drops connections under load."""
    for k in range(attempts):
        try:
            with requests.get(url, headers=hx._HEADERS, timeout=300, stream=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    f.writelines(r.iter_content(1 << 20))
            return
        except requests.RequestException:
            if k == attempts - 1:
                raise
            time.sleep(5 * 2**k)


def process_report(firm_id: str, rep: dict) -> tuple[dict, list[dict]]:
    """Download one report into a temporary directory, extract counts and KPI pages, discard the PDF.
    A complete cached copy (PDF with its page-text file, from earlier runs) is used if present."""
    cached = hx._pdf_path(int(rep["stock_code"]), rep["url"])
    with tempfile.TemporaryDirectory() as tmp:
        if cached.exists() and cached.with_suffix(".txt").exists():
            pages = hx.pdf_pages(cached)
        else:
            pdf = Path(tmp) / rep["url"].rsplit("/", 1)[-1]
            _download(rep["url"], pdf)
            pages = hx.pdf_pages(pdf)
    meta = {"firm_id": firm_id, **{k: rep[k] for k in ("stock_code", "doc_type", "filing_date", "fiscal_year", "title", "url", "size")}}
    doc_id = rep["url"].rsplit("/", 1)[-1].removesuffix(".pdf")
    write_metrics("hk", {"firm_id": firm_id, "year": int(rep["fiscal_year"]), "form": rep["doc_type"], "filing_date": rep["filing_date"],
                         "accession": doc_id, "title": rep["title"], "url": rep["url"]}, document_metrics("\n".join(pages)))
    report = {**meta, "n_pages": len(pages)}
    keep = [{"firm_id": firm_id, "url": rep["url"], "doc_type": rep["doc_type"], "fiscal_year": rep["fiscal_year"], **p} for p in kpi_pages(pages)]
    return report, keep


def pick_reports(reports: pd.DataFrame) -> pd.DataFrame:
    """Per firm and fiscal year keep the standalone ESG report if there is one, else the annual report."""
    pref = reports.assign(_t=reports["doc_type"].map({"esg_report": 1, "annual_report": 0}))
    pref = pref.sort_values(["firm_id", "fiscal_year", "_t", "filing_date"], ascending=[True, True, False, False])
    return pref.drop_duplicates(["firm_id", "fiscal_year"]).drop(columns="_t").reset_index(drop=True)


def chosen_pages(kpi: pd.DataFrame, url: str, category: str = "ghg") -> list[tuple[int, str]]:
    """Stored pages of one report and category in page order, as (page, text) for the extractor prompt."""
    g = kpi[(kpi["url"] == url) & (kpi["category"] == category)].sort_values("page")
    return list(zip(g["page"].astype(int), g["text"], strict=True))


def cache_key(rep: pd.Series | dict) -> str:
    """Key of a report in the model-answer cache: its URL, which is the same on every machine
    (a local file path would differ between a laptop and a Cloud Run task)."""
    return str(rep["url"])
