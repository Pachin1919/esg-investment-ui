"""Source-finding tools: exchange report index, company website and links, news search, catalogue merge."""

from __future__ import annotations

import pandas as pd

from esgx.ingest import news_gdelt as _news
from esgx.ingest import sources as _src
from esgx.ingest import web_pages as _web
from pipeline.tools.base import tool


@tool(kind="api", cost="network")
def report_sources(universe: str, firm_id: str, firm: dict, start: str = "2020-01-01") -> pd.DataFrame:
    """Annual, interim / quarterly and ESG reports of one firm from the exchange archive (HKEXnews)."""
    if universe == "hk":
        return _src.report_sources_hk(firm_id, int(firm["hkex_sid"]), start=start)
    raise ValueError(f"no exchange report archive wired for universe {universe!r} (Taiwan reports are a later build)")


@tool(kind="api", cost="network")
def company_website(firm_id: str) -> str | None:
    """Homepage URL of a firm from yfinance (None if unknown)."""
    return _web.company_website(firm_id)


@tool(kind="scrape", cost="network")
def website_links(url: str, max_links: int = 150) -> list[dict]:
    """Fetch a page and return its same-site links as [{'text', 'url'}]."""
    return _web.page_links(_web.fetch_html(url), url, max_links=max_links)


@tool(kind="compute", cost="free")
def about_page_heuristic(links: list[dict]) -> dict | None:
    """Keyword fallback for the about page (English and Chinese hints); used when no model call is allowed."""
    return _web.heuristic_about(links)


@tool(kind="api", cost="network")
def news_search(firm_name: str, start: str, end: str | None = None, max_records: int = 50, esg_only: bool = True) -> list[dict]:
    """News articles naming the firm from GDELT (title, url, date, publisher, language); max one call per 5 s."""
    return _news.search_news(firm_name, start, end=end, max_records=max_records, esg_only=esg_only)


@tool(kind="compute", cost="free")
def merge_sources(existing: pd.DataFrame | None, rows: list[dict] | pd.DataFrame) -> pd.DataFrame:
    """Append rows to the run's `sources` table, validated and de-duplicated on (firm_id, url)."""
    new = rows if isinstance(rows, pd.DataFrame) else _src.sources_frame(rows)
    return _src.merge_sources(existing, new)
