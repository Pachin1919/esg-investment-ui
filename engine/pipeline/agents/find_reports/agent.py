"""Report finder agent: annual, interim / quarterly and ESG reports from the exchange archive (deterministic)."""

from __future__ import annotations

from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    firms = task.tools.load_universe(task.spec.universe).set_index("firm_id")
    start = task.param("start") or task.spec.start
    wanted = set(task.param("types") or [])
    n = 0
    for t in task.tickers:
        if t not in firms.index:
            task.log(f"skip {t}: not in universe")
            continue
        found = task.tools.report_sources(task.spec.universe, t, firms.loc[t].to_dict(), start=start)
        if wanted:
            found = found[found["source_type"].isin(wanted)]
        task.ctx["sources"] = task.tools.merge_sources(task.ctx.get("sources"), found)
        n += len(found)
        task.log(f"{t}: {found['source_type'].value_counts().to_dict() if len(found) else 'no reports'}")
    return {"reports": n}


AGENT = AgentDefinition(
    id="find_reports", kind="find_reports", name="Find reports",
    role="Report finder",
    description="Lists annual, interim, quarterly and ESG reports per firm from the exchange archive (HKEXnews for HK, SEC EDGAR for US) with filing dates. No search engine and no model: the archive is complete and dated.",
    tools=("load_universe", "report_sources", "merge_sources"),
    inputs=("tickers", "spec.universe", "spec.start"), outputs=("ctx.sources",),
    default_params={"types": ["annual_report", "interim_report", "quarterly_report", "esg_report"]},
    enabled_by_default=False,
    run=run,
)
