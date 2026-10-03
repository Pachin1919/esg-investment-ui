"""About-page finder agent: locates the firm's own description of itself on its website (LLM picks the link)."""

from __future__ import annotations

import pandas as pd

from esgx import llm
from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    firms = task.tools.load_universe(task.spec.universe).set_index("firm_id")
    found = 0
    for t in task.tickers:
        if t not in firms.index:
            task.log(f"skip {t}: not in universe")
            continue
        site = task.tools.company_website(t)
        if not site:
            task.log(f"{t}: no website known")
            continue
        try:
            links = task.tools.website_links(site, max_links=int(task.param("max_links", 150)))
        except Exception as e:  # noqa: BLE001 - one unreachable site must not fail the run
            task.log(f"{t}: could not read {site} ({type(e).__name__})")
            continue
        pick = task.tools.llm_pick_about_page(task.mode, task.agent, firms.loc[t, "name"], links)
        if not pick["url"]:
            task.log(f"{t}: no about page among {len(links)} links ({pick['reason']})")
            continue
        row = {"firm_id": t, "source_type": "about_page", "title": pick["title"] or "About", "url": pick["url"],
               "date": pd.Timestamp.today().strftime("%Y-%m-%d"), "language": "", "publisher": site,
               "found_by": f"find_about_page:{pick['model']}", "relevance": 1.0, "note": pick["reason"]}
        task.ctx["sources"] = task.tools.merge_sources(task.ctx.get("sources"), [row])
        found += 1
        task.log(f"{t}: {pick['url']}")
    return {"about_pages": found}


AGENT = AgentDefinition(
    id="find_about_page", kind="find_about_page", name="Find about page",
    role="Website scout",
    description="Reads the links on the firm's homepage and picks the about-us / company-profile page. The page is the firm describing itself, so it is a TALK source. The date is the retrieval date: web pages are undated.",
    tools=("load_universe", "company_website", "website_links", "about_page_heuristic", "llm_pick_about_page", "merge_sources"),
    inputs=("tickers", "spec.universe"), outputs=("ctx.sources",),
    llm=True, default_model=llm.PRIMARY_MODEL, default_effort="low",
    default_params={"max_links": 150},
    enabled_by_default=False,
    run=run,
)
