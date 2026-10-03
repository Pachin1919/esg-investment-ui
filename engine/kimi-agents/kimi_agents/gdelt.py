"""News articles about a firm from the GDELT DOC 2.0 API (free, no key, global, multilingual).

Engle et al. (2020) build a climate news index from newspaper text; Gourier & Mathurin (2025)
label articles with an LLM under strict rules. Here we only *find* candidate articles: GDELT
returns URL, title, the time it first saw the article, domain, language and source country.
Whether an article is really about the firm and about ESG is decided downstream.

Limits: one request per 5 seconds per IP (enforced here, with back-off on HTTP 429); `seendate` is when GDELT crawled the page,
used as the publication date; titles only, no article text.
"""

from __future__ import annotations

import time

import pandas as pd
import requests

API = "https://api.gdeltproject.org/api/v2/doc/doc"
ESG_QUERY = "(climate OR emissions OR carbon OR ESG OR sustainability OR environmental OR greenwashing)"
MIN_INTERVAL = 6.0
_last_call = 0.0


def build_query(firm_name: str, esg_only: bool = True) -> str:
    """Exact-phrase firm name, optionally AND-ed with ESG terms. Legal suffixes are dropped."""
    name = firm_name
    for suffix in (" Limited", " Ltd.", " Ltd", " Inc.", " Inc", " Corporation", " Corp.", " Corp", " PLC", " plc"):
        name = name.strip(" ,").removesuffix(suffix)
    q = f'"{name.strip(" ,.")}"'
    return f"{q} {ESG_QUERY}" if esg_only else q


def _stamp(date: str) -> str:
    return pd.Timestamp(date).strftime("%Y%m%d%H%M%S")


def search_news(firm_name: str, start: str, end: str | None = None, max_records: int = 50, esg_only: bool = True) -> list[dict]:
    """Articles as [{'title', 'url', 'date', 'publisher', 'language', 'country'}], most relevant first (GDELT `hybridrel`)."""
    global _last_call
    wait = MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    params = {"query": build_query(firm_name, esg_only), "mode": "artlist", "format": "json", "sort": "hybridrel",
              "maxrecords": min(int(max_records), 250), "startdatetime": _stamp(start),
              "enddatetime": _stamp(end or pd.Timestamp.today().strftime("%Y-%m-%d"))}
    for backoff in (0, 20, 45):  # GDELT throttles by IP and keeps answering 429 for a while after a burst
        time.sleep(backoff)
        r = requests.get(API, params=params, headers={"User-Agent": "esgx research"}, timeout=60)
        _last_call = time.time()
        if r.status_code != 429:
            break
    r.raise_for_status()
    try:
        articles = r.json().get("articles", [])
    except ValueError:  # GDELT answers plain text for empty or malformed queries
        return []
    return [
        {"title": a.get("title", "").strip(), "url": a["url"],
         "date": pd.to_datetime(a["seendate"], format="%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d"),
         "publisher": a.get("domain", ""), "language": a.get("language", ""), "country": a.get("sourcecountry", "")}
        for a in articles if a.get("url") and a.get("seendate")
    ]
