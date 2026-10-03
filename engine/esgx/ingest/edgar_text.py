"""Firm documents from SEC EDGAR for the talk/walk pipeline.

Sources (all free, User-Agent required):
* submissions API  https://data.sec.gov/submissions/CIK##########.json  -> filing index
* archives         https://www.sec.gov/Archives/edgar/data/<cik>/<acc-no-dashes>/<doc>

Document types
--------------
* 10-K  : annual report. We keep Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A).
* 10-Q  : quarterly report. Item 2 (MD&A) + risk-factor updates.
* 8-K   : announcements; the press release is usually exhibit EX-99.1.

Output is a `documents` table: firm_id, cik, form, filing_date, period, accession,
section, text. Raw HTML is cached under data/raw/edgar/<cik>/. Parsing (HTML to text, item
splitting, climate-passage filter) lives in `edgar_sections.py`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd
import requests
from bs4 import BeautifulSoup

from esgx.config import RAW_DIR, SEC_USER_AGENT
from esgx.ingest.edgar_sections import (
    CLIMATE_TERMS,
    MIN_SECTION_CHARS,
    SECTIONS_10K,
    SECTIONS_10Q,
    climate_passages,
    html_to_text,
    split_items,
)

__all__ = [
    "CLIMATE_TERMS",
    "MIN_SECTION_CHARS",
    "SECTIONS_10K",
    "SECTIONS_10Q",
    "Filing",
    "climate_passages",
    "fetch_document",
    "html_to_text",
    "list_filings",
    "load_documents",
    "press_release_docs",
    "split_items",
]

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
INDEX_JSON = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json"

_session = requests.Session()
_session.headers.update({"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})


def _get(url: str, *, sleep: float = 0.11, **kw) -> requests.Response:
    r = _session.get(url, timeout=60, **kw)
    time.sleep(sleep)  # SEC fair-access limit: 10 req/s
    r.raise_for_status()
    return r


@dataclass
class Filing:
    cik: int
    form: str
    filing_date: str
    report_date: str
    accession: str  # with dashes
    primary_doc: str

    @property
    def acc_nodash(self) -> str:
        return self.accession.replace("-", "")


# Re-incorporations create a new registrant CIK; EDGAR does not link successor and predecessor.
# Map new CIK -> older CIKs whose filings belong to the same firm (extend as cases appear).
PREDECESSOR_CIKS: dict[int, list[int]] = {
    2115436: [34088],  # ExxonMobil (Texas re-domicile 2026) -> Exxon Mobil Corp (NJ)
}


def list_filings(cik: int, forms: tuple[str, ...] = ("10-K", "10-Q", "8-K"), start: str = "2015-01-01") -> list[Filing]:
    """All filings of the given forms since `start`, newest first, across the firm's CIK and any
    predecessor CIKs (see PREDECESSOR_CIKS)."""
    out: list[Filing] = []
    for c in [cik] + PREDECESSOR_CIKS.get(cik, []):
        out.extend(_list_filings_one(c, forms, start))
    return sorted(out, key=lambda f: f.filing_date, reverse=True)


def _list_filings_one(cik: int, forms: tuple[str, ...], start: str) -> list[Filing]:
    d = _get(SUBMISSIONS.format(cik=cik)).json()
    frames = [pd.DataFrame(d["filings"]["recent"])]
    for f in d["filings"].get("files", []):
        frames.append(pd.DataFrame(_get("https://data.sec.gov/submissions/" + f["name"]).json()))
    df = pd.concat(frames, ignore_index=True)
    df = df[df["form"].isin(forms) & (df["filingDate"] >= start)]
    return [
        Filing(cik, r.form, r.filingDate, r.reportDate, r.accessionNumber, r.primaryDocument)
        for r in df.itertuples()
    ]


def _cache_path(cik: int, acc: str, doc: str):
    p = RAW_DIR / "edgar" / str(cik) / acc
    p.mkdir(parents=True, exist_ok=True)
    return p / doc


def fetch_document(cik: int, acc_nodash: str, doc: str) -> str:
    path = _cache_path(cik, acc_nodash, doc)
    if path.exists():
        return path.read_text(errors="ignore")
    html = _get(ARCHIVE.format(cik=cik, acc=acc_nodash, doc=doc)).text
    path.write_text(html)
    return html


INDEX_HTML = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{accdash}-index.html"


def press_release_docs(cik: int, acc_nodash: str, accession: str) -> list[str]:
    """Documents typed EX-99.* on the filing index page (press releases / earnings releases).
    Exhibit file names are not standardised, so we read the Type column instead."""
    try:
        html = _get(INDEX_HTML.format(cik=cik, acc=acc_nodash, accdash=accession)).text
    except requests.HTTPError:
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.select("table.tableFile tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        a = tr.find("a", href=True)
        if len(tds) >= 4 and a and tds[3].upper().startswith("EX-99"):
            name = a["href"].rsplit("/", 1)[-1]
            if name.lower().endswith((".htm", ".html")):
                out.append(name)
    return out


def load_documents(firm_id: str, cik: int, forms: tuple[str, ...] = ("10-K", "10-Q", "8-K"), start: str = "2015-01-01", max_8k: int = 40) -> pd.DataFrame:
    """Build the documents table for one firm (cached HTML, re-parsed each call)."""
    rows = []
    n8k = 0
    for f in list_filings(cik, forms, start):
        if f.form == "8-K":
            if n8k >= max_8k:
                continue
            for doc in press_release_docs(f.cik, f.acc_nodash, f.accession):
                txt = html_to_text(fetch_document(f.cik, f.acc_nodash, doc))
                if len(txt) < 500:
                    continue
                rows.append({**_base(firm_id, f), "section": "press_release", "text": txt})
                n8k += 1
            continue
        txt = html_to_text(fetch_document(f.cik, f.acc_nodash, f.primary_doc))
        wanted = SECTIONS_10K if f.form == "10-K" else SECTIONS_10Q
        for sec, body in split_items(txt, wanted).items():
            if len(body) >= MIN_SECTION_CHARS:  # cross-reference stubs ("see Financial Section") are dropped
                rows.append({**_base(firm_id, f), "section": sec, "text": body})
        # whole-document climate passages: robust to filers that put MD&A outside Item 7
        rows.append({**_base(firm_id, f), "section": "full_climate", "text": climate_passages(txt, max_chars=120_000)[0]})
    return pd.DataFrame(rows, columns=["firm_id", "cik", "form", "filing_date", "period", "accession", "section", "text"])


def _base(firm_id: str, f: Filing) -> dict:
    return {"firm_id": firm_id, "cik": f.cik, "form": f.form, "filing_date": f.filing_date, "period": f.report_date, "accession": f.accession}
