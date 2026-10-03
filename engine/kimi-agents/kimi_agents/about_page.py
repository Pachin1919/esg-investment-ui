"""About-page finder: the model picks the firm's own description of itself among its homepage links.

The answer is an index into the supplied list, so the model cannot invent a URL. Without a key
(or with `live=False`) a keyword heuristic is used; heuristic output is for testing only.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

from kimi_agents import MODEL, web
from kimi_agents.client import kimi_parse

SYSTEM_PROMPT = """You are given the links found on a company's homepage as a numbered list (link text and URL).
Pick the ONE link that leads to the company's own description of itself: "About us", company profile,
corporate overview, who we are (any language). Rules: choose only from the list, by its number. Do not
invent a URL. Prefer the general company overview over investor relations, careers, news, history or
sustainability pages. If no link fits, answer index -1."""


class AboutPick(BaseModel):
    index: int = Field(description="Number of the chosen link in the list, or -1 if none fits")
    reason: str = Field(description="One short sentence")


def pick(firm_name: str, links: list[dict], live: bool = True, model: str = MODEL) -> dict:
    """{'url', 'title', 'reason', 'found_by'}; url is None when nothing fits."""
    if not links:
        return {"url": None, "title": "", "reason": "no links on the homepage", "found_by": "about_page"}
    if not live:
        hit = web.heuristic_about(links)
        return {"url": hit["url"] if hit else None, "title": hit["text"] if hit else "", "reason": "keyword heuristic", "found_by": "about_page:heuristic"}
    listing = "\n".join(f"{i}. {x['text'] or '(no text)'} | {x['url']}" for i, x in enumerate(links))
    choice, _ = kimi_parse(SYSTEM_PROMPT, f"COMPANY: {firm_name}\n\nLINKS:\n{listing}", AboutPick, model=model, max_tokens=2000)
    ok = 0 <= choice.index < len(links)
    return {"url": links[choice.index]["url"] if ok else None, "title": links[choice.index]["text"] if ok else "",
            "reason": choice.reason, "found_by": f"about_page:{model}"}


def run(firm_id: str, firm_name: str, live: bool = True, site: str | None = None, max_links: int = 150) -> tuple[list[dict], str]:
    """(`sources` rows, log line) for one firm. Sites that block automated requests are skipped, not worked around."""
    site = site or web.company_website(firm_id)
    if not site:
        return [], "no website known"
    try:
        links = web.page_links(web.fetch_html(site), site, max_links=max_links)
    except Exception as e:  # noqa: BLE001 - one unreachable site must not stop the run
        return [], f"could not read {site} ({type(e).__name__})"
    p = pick(firm_name, links, live=live)
    if not p["url"]:
        return [], f"no about page among {len(links)} links ({p['reason']})"
    row = {"firm_id": firm_id, "source_type": "about_page", "title": p["title"] or "About", "url": p["url"],
           "date": pd.Timestamp.today().strftime("%Y-%m-%d"), "language": "", "publisher": site,
           "found_by": p["found_by"], "relevance": 1.0, "note": p["reason"]}
    return [row], p["url"]
