"""News finder: GDELT search for the firm with ESG terms, then the model labels each headline.

Headlines go to the model in batches (10 per call) so no single answer gets long. A headline the
model skips is dropped, never guessed. Without a key (or `live=False`) a keyword heuristic is used.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from kimi_agents import MODEL, gdelt
from kimi_agents.client import kimi_parse

SYSTEM_PROMPT = """You are given news headlines returned by a keyword search for one company.
For each headline decide, from the headline and publisher only:
- about_firm: is this company a main subject of the article (not a passing mention, not a different company
  with a similar name)?
- esg_related: is the article about environmental, climate, social or governance matters?
- relevance: 0-10, how useful the article is for judging the company's ESG conduct or ESG claims.
Do not infer, invent or speculate beyond the headline. When unsure, answer false and a low relevance."""

_ESG_WORDS = [w.lower() for w in gdelt.ESG_QUERY.strip("()").split(" OR ")]


class NewsLabel(BaseModel):
    index: int
    about_firm: bool
    esg_related: bool
    relevance: float = Field(ge=0, le=10)


class NewsLabels(BaseModel):
    labels: list[NewsLabel]


def label(firm_name: str, articles: list[dict], live: bool = True, batch_size: int = 10, model: str = MODEL) -> list[dict]:
    """Articles with about_firm, esg_related, relevance and labelled_by added."""
    if not live:
        key = firm_name.lower().split()[0]
        return [{**a, "about_firm": key in a["title"].lower(), "esg_related": any(w in a["title"].lower() for w in _ESG_WORDS),
                 "relevance": 5.0 * (key in a["title"].lower()) + 5.0 * any(w in a["title"].lower() for w in _ESG_WORDS),
                 "labelled_by": "heuristic"} for a in articles]
    out = []
    for lo in range(0, len(articles), max(1, batch_size)):
        batch = articles[lo: lo + max(1, batch_size)]
        listing = json.dumps([{"index": i, "title": a["title"], "publisher": a.get("publisher", "")} for i, a in enumerate(batch)], ensure_ascii=False)
        parsed, _ = kimi_parse(SYSTEM_PROMPT, f"COMPANY: {firm_name}\n\nHEADLINES:\n{listing}", NewsLabels, model=model, max_tokens=4000)
        by_index = {lab.index: lab for lab in parsed.labels}
        out += [{**a, "about_firm": by_index[i].about_firm, "esg_related": by_index[i].esg_related,
                 "relevance": by_index[i].relevance, "labelled_by": model} for i, a in enumerate(batch) if i in by_index]
    return out


def run(firm_id: str, firm_name: str, start: str, live: bool = True, max_records: int = 30, min_relevance: float = 5,
        articles: list[dict] | None = None) -> tuple[list[dict], str]:
    """(`sources` rows, log line) for one firm. `articles` lets tests skip the GDELT call."""
    if articles is None:
        try:
            articles = gdelt.search_news(firm_name, start, max_records=max_records)
        except Exception as e:  # noqa: BLE001 - a failed search for one firm must not stop the run
            return [], f"news search failed ({type(e).__name__})"
    rows = [{"firm_id": firm_id, "source_type": "news", "title": a["title"], "url": a["url"], "date": a["date"],
             "language": a.get("language", ""), "publisher": a.get("publisher", ""), "found_by": f"news:{a['labelled_by']}",
             "relevance": a["relevance"], "note": "esg" if a["esg_related"] else "not esg"}
            for a in label(firm_name, articles, live=live) if a["about_firm"] and a["relevance"] >= min_relevance]
    return rows, f"{len(articles)} hits, {len(rows)} kept"
