"""LLM tools for the source finders: pick the about page among a site's links, label news hits.

Prompt discipline follows Gourier & Mathurin (2025): choose only from what is supplied, do not
infer, invent or speculate. Outside live mode both tools fall back to keyword heuristics so the
pipeline can be tested for free; heuristic output is never a result.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from esgx import llm
from esgx.ingest.news_gdelt import ESG_QUERY
from esgx.ingest.web_pages import heuristic_about
from pipeline.spec import AgentSpec, Mode
from pipeline.tools.base import tool

ABOUT_PROMPT = """You are given the links found on a company's homepage as a numbered list (link text and URL).
Pick the ONE link that leads to the company's own description of itself: "About us", company profile,
corporate overview, who we are (any language). Rules: choose only from the list, by its number. Do not
invent a URL. Prefer the general company overview over investor relations, careers, news, history or
sustainability pages. If no link fits, answer index -1."""

NEWS_PROMPT = """You are given news headlines returned by a keyword search for one company.
For each headline decide, from the headline and publisher only:
- about_firm: is this company a main subject of the article (not a passing mention, not a different company
  with a similar name)?
- esg_related: is the article about environmental, climate, social or governance matters?
- relevance: 0-10, how useful the article is for judging the company's ESG conduct or ESG claims.
Do not infer, invent or speculate beyond the headline. When unsure, answer false and a low relevance."""

_ESG_WORDS = [w.lower() for w in ESG_QUERY.strip("()").split(" OR ")]


class AboutPick(BaseModel):
    index: int = Field(description="Number of the chosen link in the list, or -1 if none fits")
    reason: str = Field(description="One short sentence")


class NewsLabel(BaseModel):
    index: int
    about_firm: bool
    esg_related: bool
    relevance: float = Field(ge=0, le=10)


class NewsLabels(BaseModel):
    labels: list[NewsLabel]


def _system(base: str, agent: AgentSpec) -> str:
    return base + (f"\n\n{agent.role_prompt}" if agent.role_prompt.strip() else "")


@tool(kind="llm", cost="paid")
def llm_pick_about_page(mode: Mode, agent: AgentSpec, firm_name: str, links: list[dict]) -> dict:
    """Choose the about-us link among a homepage's links; keyword heuristic unless mode is live."""
    if not links:
        return {"url": None, "title": "", "reason": "no links", "model": mode}
    if mode != "live":
        hit = heuristic_about(links)
        return {"url": hit["url"] if hit else None, "title": hit["text"] if hit else "", "reason": "keyword heuristic", "model": mode}
    listing = "\n".join(f"{i}. {x['text'] or '(no text)'} | {x['url']}" for i, x in enumerate(links))
    pick, usage = llm.parse(agent.model, _system(ABOUT_PROMPT, agent), f"COMPANY: {firm_name}\n\nLINKS:\n{listing}", AboutPick,
                            effort=agent.effort, max_tokens=2000)
    ok = 0 <= pick.index < len(links)
    return {"url": links[pick.index]["url"] if ok else None, "title": links[pick.index]["text"] if ok else "",
            "reason": pick.reason, "model": agent.model, "usage": usage}


@tool(kind="llm", cost="paid")
def llm_filter_news(mode: Mode, agent: AgentSpec, firm_name: str, articles: list[dict], batch_size: int = 10) -> list[dict]:
    """Label news hits (about the firm? ESG-related? relevance 0-10) in batches of `batch_size` headlines per
    model call; keyword heuristic unless mode is live. A headline the model skips is dropped, never guessed."""
    if not articles:
        return []
    if mode != "live":
        key = firm_name.lower().split()[0]
        out = []
        for a in articles:
            t = a["title"].lower()
            about, esg = key in t, any(w in t for w in _ESG_WORDS)
            out.append({**a, "about_firm": about, "esg_related": esg, "relevance": 5.0 * about + 5.0 * esg, "model": mode})
        return out
    out = []
    for lo in range(0, len(articles), max(1, batch_size)):
        batch = articles[lo: lo + max(1, batch_size)]
        listing = json.dumps([{"index": i, "title": a["title"], "publisher": a.get("publisher", "")} for i, a in enumerate(batch)], ensure_ascii=False)
        parsed, _ = llm.parse(agent.model, _system(NEWS_PROMPT, agent), f"COMPANY: {firm_name}\n\nHEADLINES:\n{listing}", NewsLabels,
                              effort=agent.effort, max_tokens=4000)
        by_index = {lab.index: lab for lab in parsed.labels}
        out += [{**a, "about_firm": by_index[i].about_firm, "esg_related": by_index[i].esg_related,
                 "relevance": by_index[i].relevance, "model": agent.model}
                for i, a in enumerate(batch) if i in by_index]
    return out
