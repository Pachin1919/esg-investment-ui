"""Annual and ESG reports of SEHK-listed firms from HKEXnews (free, no key).

API (undocumented but stable): titleSearchServlet.do returns JSON rows with
STOCK_CODE, TITLE, DATE_TIME, FILE_LINK (PDF under https://www1.hkexnews.hk).
Category t1code=40000 = "Financial Statements / ESG Information", which holds annual
reports and standalone ESG / sustainability reports. `stockId` is HKEX's internal id
(see `universe_hk.load_hkex_stock_map`).

HKEX ESG Reporting Guide (Appendix C2, mandatory KPIs since FY2020): A1.2 requires
scope 1 and scope 2 GHG emissions in tonnes and intensity. From 1 Jan 2025 the new
climate requirements (Part D, ISSB-aligned) phase in. So every report since FY2020
should contain scope 1 and 2; that is what `emissions_hk` extracts.

Output `documents_hk` table: firm_id, stock_code, doc_type, filing_date, period (FY end),
title, url, path, n_pages. PDFs cached under data/raw/hkex/<code>/, page text as .txt
with form-feed page separators (pdftotext -layout, pypdf fallback).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pandas as pd
import requests

from esgx.config import RAW_DIR

SEARCH = "https://www1.hkexnews.hk/search/titleSearchServlet.do"
BASE = "https://www1.hkexnews.hk"
_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)"}
CACHE = RAW_DIR / "hkex"

_ESG_RE = re.compile(r"\b(esg|environmental, social|sustainab|climate)", re.IGNORECASE)
_ANNUAL_RE = re.compile(r"\bannual report\b", re.IGNORECASE)
_INTERIM_RE = re.compile(r"\binterim\b|\bquarterly\b|half-year", re.IGNORECASE)
_YEAR_RE = re.compile(r"(20\d{2})(?:/(\d{2}))?")


_QUARTERLY_RE = re.compile(r"\bquarterly\b|\b(first|third)[- ]quarter", re.IGNORECASE)
DEFAULT_KINDS = ("annual_report", "esg_report")
ALL_KINDS = ("annual_report", "esg_report", "interim_report", "quarterly_report")


def classify_title(title: str) -> str | None:
    """'annual_report' | 'esg_report' | 'quarterly_report' | 'interim_report' | None."""
    if _QUARTERLY_RE.search(title):
        return "quarterly_report"
    if _INTERIM_RE.search(title):
        return "interim_report"
    if _ESG_RE.search(title) and not _ANNUAL_RE.search(title):
        return "esg_report"
    if _ANNUAL_RE.search(title):
        return "annual_report"
    if _ESG_RE.search(title):
        return "esg_report"
    return None


def fiscal_year_from_title(title: str, filing_date: str) -> int:
    """'2024 Annual Report' -> 2024; '2023/24 ...' -> 2024; else filing year - 1."""
    m = _YEAR_RE.search(title)
    if m:
        y = int(m.group(1))
        if m.group(2):
            return int(str(y)[:2] + m.group(2))
        return y
    return pd.Timestamp(filing_date).year - 1


def list_reports(stock_id: int, start: str = "2020-01-01", end: str | None = None, kinds: tuple[str, ...] = DEFAULT_KINDS) -> list[dict]:
    """Reports of the given kinds; the default keeps only annual and ESG reports (what `emissions_hk` reads)."""
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    params = {
        "sortDir": 0, "sortByOptions": "DateTime", "category": 0, "market": "SEHK", "stockId": int(stock_id),
        "documentType": -1, "fromDate": pd.Timestamp(start).strftime("%Y%m%d"), "toDate": pd.Timestamp(end).strftime("%Y%m%d"),
        "title": "", "searchType": 1, "t1code": 40000, "t2Gcode": -2, "t2code": -2, "rowRange": 200, "lang": "E",
    }
    r = requests.get(SEARCH, params=params, headers=_HEADERS, timeout=60)
    r.raise_for_status()
    rows = json.loads(r.json().get("result", "[]"))
    out = []
    for row in rows:  # dual-counter stocks list both codes ("00016<br/>80016"): the first is the HKD counter
        kind = classify_title(row["TITLE"])
        if kind not in kinds or row.get("FILE_TYPE", "PDF").upper() != "PDF":
            continue
        filing_date = pd.to_datetime(row["DATE_TIME"], dayfirst=True).strftime("%Y-%m-%d")
        out.append({
            "stock_code": int(str(row["STOCK_CODE"]).split("<")[0]), "doc_type": kind, "filing_date": filing_date,
            "fiscal_year": fiscal_year_from_title(row["TITLE"], filing_date), "title": row["TITLE"],
            "url": BASE + row["FILE_LINK"], "size": row.get("FILE_INFO", ""),
        })
    time.sleep(0.5)
    return out


def _pdf_path(stock_code: int, url: str) -> Path:
    d = CACHE / f"{stock_code:05d}"
    d.mkdir(parents=True, exist_ok=True)
    return d / url.rsplit("/", 1)[-1]


def fetch_pdf(stock_code: int, url: str) -> Path:
    path = _pdf_path(stock_code, url)
    if not path.exists():
        with requests.get(url, headers=_HEADERS, timeout=300, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                f.writelines(r.iter_content(1 << 20))
        time.sleep(0.5)
    return path


def pdf_pages(path: Path) -> list[str]:
    """Text per page (cached as .txt with form feeds)."""
    txt = path.with_suffix(".txt")
    if not txt.exists():
        if shutil.which("pdftotext"):
            subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), str(txt)], check=True, capture_output=True)
        else:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            txt.write_text("\f".join((p.extract_text() or "") for p in reader.pages))
    return txt.read_text(errors="ignore").split("\f")


def load_documents_hk(firm_id: str, stock_code: int, stock_id: int, start: str = "2020-01-01", download: bool = True) -> pd.DataFrame:
    rows = []
    for rep in list_reports(stock_id, start=start):
        path, n_pages = None, None
        if download:
            path = fetch_pdf(stock_code, rep["url"])
            n_pages = len(pdf_pages(path))
        rows.append({"firm_id": firm_id, **rep, "path": str(path) if path else None, "n_pages": n_pages})
    cols = ["firm_id", "stock_code", "doc_type", "filing_date", "fiscal_year", "title", "url", "size", "path", "n_pages"]
    return pd.DataFrame(rows, columns=cols)
