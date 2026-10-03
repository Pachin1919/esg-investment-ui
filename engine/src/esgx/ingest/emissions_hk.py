"""Scope 1 / 2 emissions extracted from HKEX ESG and annual reports with an LLM.

Why an LLM: there is no public emissions registry for Hong Kong. HKEX Appendix C2 KPI A1.2
makes scope 1 and 2 disclosure mandatory since FY2020, but the numbers sit in PDF tables
with firm-specific layouts. The extractor is auditable by construction: every number
comes with page number and verbatim quote, and nothing is inferred (Gourier & Mathurin
2025 prompt discipline: "do not infer, invent or speculate").

Flow: candidate pages (regex on scope / tCO2e) -> structured output (pydantic) ->
`emissions` rows (schema.py) with extras: doc_type, pages, quote, verified, confidence.
Reports usually tabulate 2-3 fiscal years, so one call yields several firm-years.

Model: the project's primary model (`esgx.llm.PRIMARY_MODEL`, Kimi K3) through `esgx.llm.parse`;
a claude-* model id routes to Anthropic as a second rater. About 6 pages x 1.5k tokens per report
(USD 0.05-0.10 per report was measured with claude-opus-5; Kimi's cost is not measured yet). Cached per (document, EXTRACT_VERSION, model) under data/raw/llm_cache/.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, Field

from esgx import llm
from esgx.config import RAW_DIR
from esgx.ingest.hkexnews import pdf_pages
from esgx.schema import validate

EXTRACT_VERSION = "v1"
DEFAULT_MODEL = llm.PRIMARY_MODEL
CACHE_DIR = RAW_DIR / "llm_cache"

_SCOPE_RE = re.compile(r"scope\s*[12]\b|scope\s*1\s*(?:and|&)\s*2", re.IGNORECASE)
_UNIT_RE = re.compile(r"tco2|tonnes?\s+(?:of\s+)?co2|t\s*co2|ktco2|co2e|co2-e|carbon dioxide equivalent", re.IGNORECASE)
_GHG_RE = re.compile(r"greenhouse gas|ghg emissions?", re.IGNORECASE)


class YearRow(BaseModel):
    fiscal_year: int = Field(description="Reporting year the figures refer to, e.g. 2024 for FY2024 or FY2023/24.")
    scope1_tco2e: float | None = Field(None, description="Scope 1 in tonnes CO2e (convert from kt or thousand tonnes). null if not stated.")
    scope2_tco2e: float | None = Field(None, description="Scope 2 in tonnes CO2e. Location-based if both bases are given. null if not stated.")
    scope2_basis: str | None = Field(None, description="'location' | 'market' | 'unspecified'")
    scope3_tco2e: float | None = Field(None, description="Scope 3 total in tonnes CO2e if explicitly stated, else null.")
    intensity_value: float | None = Field(None, description="Reported GHG intensity (scope 1+2) if stated, as printed.")
    intensity_unit: str | None = Field(None, description="Unit of the reported intensity exactly as printed, e.g. 'tCO2e per HK$ million revenue'.")


class Evidence(BaseModel):
    page: int = Field(description="1-based page number in the PDF as given in the page header of the input.")
    quote: str = Field(description="Verbatim text from that page containing the number(s), max 300 characters.")


class EmissionsExtraction(BaseModel):
    found: bool = Field(description="True only if at least one scope 1 or scope 2 figure is explicitly stated.")
    series: list[YearRow] = Field(default_factory=list, description="One entry per fiscal year tabulated in the report, most recent first.")
    boundary: str | None = Field(None, description="Reporting boundary as stated (e.g. 'Hong Kong operations only', 'Group-wide'). null if not stated.")
    third_party_assured: bool | None = Field(None, description="True if an independent assurance/verification statement covers the GHG figures; null if unclear.")
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(description="0-1. Below 0.5 if units are ambiguous, tables are garbled, or figures conflict across pages.")
    notes: str = Field("", description="Any caveat needed to interpret the numbers (restatements, unit ambiguity, subsidiaries). Max 300 chars.")


SYSTEM_PROMPT = """You extract greenhouse-gas emission figures from Hong Kong listed-company ESG or annual reports.

Rules
- Report ONLY figures that are explicitly stated in the supplied pages. Do not infer, invent, estimate or speculate. If a figure is absent, use null.
- Convert to tonnes CO2e: kilotonnes / thousand tonnes x 1000; million tonnes x 1,000,000. Never change the reported intensity value; copy its unit verbatim.
- Scope 2: prefer the location-based figure when both bases are given, and say which basis you used.
- If the same table lists several fiscal years, return one entry per year. Fiscal year = the year the figures refer to (FY2023/24 -> 2024).
- If figures conflict across pages, choose the one in the KPI / performance data table, lower the confidence, and explain in notes.
- Every returned number must be backed by an evidence item with the page number and a verbatim quote.
- Ignore targets, baselines, avoided emissions and intensity-only tables when computing scope totals."""


class ExtractClient(Protocol):
    model: str

    def extract(self, system: str, user: str) -> tuple[EmissionsExtraction, dict]: ...


@dataclass
class LiveExtractClient:
    """Paid structured-output call through `esgx.llm.parse` (Kimi or Claude, decided by the model id)."""

    model: str = DEFAULT_MODEL
    effort: str = "medium"
    max_tokens: int = 6000

    def extract(self, system: str, user: str) -> tuple[EmissionsExtraction, dict]:
        return llm.parse(self.model, system, user, EmissionsExtraction, effort=self.effort, max_tokens=self.max_tokens)


ClaudeExtractClient = LiveExtractClient  # name kept for callers


def candidate_pages(pages: list[str], top_k: int = 6, max_chars: int = 7000) -> list[tuple[int, str]]:
    """Pages most likely to hold the GHG table: scored by scope/unit/GHG hits, keep top_k in page order."""
    scored = []
    for i, p in enumerate(pages, start=1):
        s = 3 * len(_SCOPE_RE.findall(p)) + 2 * len(_UNIT_RE.findall(p)) + len(_GHG_RE.findall(p))
        if s > 0:
            scored.append((s, i))
    keep = sorted(i for _, i in sorted(scored, reverse=True)[:top_k])
    return [(i, pages[i - 1][:max_chars]) for i in keep]


def _user_prompt(firm_name: str, title: str, fiscal_year: int, chosen: list[tuple[int, str]]) -> str:
    head = f"Company: {firm_name}\nDocument: {title} (fiscal year {fiscal_year})\n\nPages (1-based PDF page numbers):\n"
    body = "\n".join(f"\n===== PAGE {i} =====\n{t}" for i, t in chosen)
    return head + body


def _cache_path(doc_path: str, model: str) -> Path:
    h = hashlib.sha1(f"{EXTRACT_VERSION}|{model}|{doc_path}".encode()).hexdigest()[:20]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"em_{h}.json"


def extract_document(client: ExtractClient, firm_name: str, doc: pd.Series, top_k: int = 6) -> tuple[EmissionsExtraction | None, dict]:
    """Run extraction on one `documents_hk` row (cached). Returns (parsed, usage); parsed None if no candidate pages."""
    return extract_pages(client, firm_name, doc, candidate_pages(pdf_pages(Path(doc["path"])), top_k=top_k), doc["path"])


def extract_pages(client: ExtractClient, firm_name: str, doc: pd.Series, chosen: list[tuple[int, str]], key: str) -> tuple[EmissionsExtraction | None, dict]:
    """Extraction from already selected (page, text) pairs; `key` identifies the document in the cache.
    Lets the streaming ingest extract from stored KPI pages after the PDF has been discarded."""
    if not chosen:
        return None, {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "model": client.model, "n_pages_sent": 0}
    path = _cache_path(key, client.model)
    if path.exists():
        c = json.loads(path.read_text())
        return EmissionsExtraction.model_validate(c["extraction"]), c["usage"]
    parsed, usage = client.extract(SYSTEM_PROMPT, _user_prompt(firm_name, doc["title"], int(doc["fiscal_year"]), chosen))
    usage["n_pages_sent"] = len(chosen)
    path.write_text(json.dumps({"extraction": parsed.model_dump(), "usage": usage}))
    return parsed, usage


def rows_from_extraction(doc: pd.Series, ex: EmissionsExtraction) -> list[dict]:
    pages = sorted({e.page for e in ex.evidence})
    quote = ex.evidence[0].quote if ex.evidence else ""
    out = []
    for yr in ex.series:
        if yr.scope1_tco2e is None and yr.scope2_tco2e is None:
            continue
        out.append({
            "firm_id": doc["firm_id"], "year": int(yr.fiscal_year), "scope1": yr.scope1_tco2e, "scope2": yr.scope2_tco2e,
            "scope3": yr.scope3_tco2e, "source": "hkex_esg_report", "matched": True,
            "scope2_basis": yr.scope2_basis, "intensity_reported": yr.intensity_value, "intensity_unit": yr.intensity_unit,
            "doc_type": doc["doc_type"], "doc_fiscal_year": int(doc["fiscal_year"]), "doc_url": doc["url"], "pages": ",".join(map(str, pages)),
            "quote": quote, "boundary": ex.boundary, "verified": ex.third_party_assured, "confidence": ex.confidence, "notes": ex.notes,
        })
    return out


def consolidate(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per firm-year: prefer the most recent document (restatements win), then ESG report over
    annual report, then higher confidence. Keeps all columns of the winning row."""
    if rows.empty:
        return rows
    pref = rows.assign(_t=rows["doc_type"].map({"esg_report": 1, "annual_report": 0}).fillna(0))
    pref = pref.sort_values(["firm_id", "year", "doc_fiscal_year", "_t", "confidence"], ascending=[True, True, False, False, False])
    out = pref.drop_duplicates(["firm_id", "year"], keep="first").drop(columns="_t").reset_index(drop=True)
    return validate(out, "emissions")
