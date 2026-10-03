"""News finder agent: GDELT search per firm, then an LLM keeps the articles that are about the firm and ESG."""

from __future__ import annotations

from esgx import llm
from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    firms = task.tools.load_universe(task.spec.universe).set_index("firm_id")
    start = task.param("start") or task.spec.start
    min_rel = float(task.param("min_relevance", 5))
    hits = kept = 0
    for t in task.tickers:
        if t not in firms.index:
            task.log(f"skip {t}: not in universe")
            continue
        name = firms.loc[t, "name"]
        try:
            articles = task.tools.news_search(name, start, max_records=int(task.param("max_records", 50)),
                                              esg_only=bool(task.param("esg_only", True)))
        except Exception as e:  # noqa: BLE001 - a failed search for one firm must not fail the run
            task.log(f"{t}: news search failed ({type(e).__name__})")
            continue
        labelled = task.tools.llm_filter_news(task.mode, task.agent, name, articles, batch_size=int(task.param("batch_size", 10)))
        rows = [
            {"firm_id": t, "source_type": "news", "title": a["title"], "url": a["url"], "date": a["date"],
             "language": a.get("language", ""), "publisher": a.get("publisher", ""), "found_by": f"find_news:{a['model']}",
             "relevance": a["relevance"], "note": "esg" if a["esg_related"] else "not esg"}
            for a in labelled if a["about_firm"] and a["relevance"] >= min_rel
        ]
        task.ctx["sources"] = task.tools.merge_sources(task.ctx.get("sources"), rows)
        hits += len(articles)
        kept += len(rows)
        task.log(f"{t}: {len(articles)} hits, {len(rows)} kept")
    return {"hits": hits, "kept": kept}


AGENT = AgentDefinition(
    id="find_news", kind="find_news", name="Find news",
    role="News scout",
    description="Searches GDELT for articles naming the firm together with ESG terms, then labels each headline (about the firm? ESG-related? relevance 0-10) and keeps the relevant ones with their publication date. News is a TALK / salience source and never enters the walk pillar.",
    tools=("load_universe", "news_search", "llm_filter_news", "merge_sources"),
    inputs=("tickers", "spec.universe", "spec.start"), outputs=("ctx.sources",),
    llm=True, default_model=llm.PRIMARY_MODEL, default_effort="low",
    default_params={"max_records": 50, "min_relevance": 5, "esg_only": True, "batch_size": 10},
    enabled_by_default=False,
    run=run,
)
