"""Hard-data agent: the facts the text will be checked against (deterministic, local tables)."""

from __future__ import annotations

import pandas as pd

from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    docs = task.ctx.get("documents", pd.DataFrame())
    hd: dict[tuple[str, int], dict] = {}
    for r in docs.itertuples():
        year = pd.to_datetime(r.period).year if getattr(r, "period", None) else pd.to_datetime(r.filing_date).year
        hd.setdefault((r.firm_id, year), task.tools.firm_hard_data(r.firm_id, year, task.spec.universe))
    task.ctx["hard_data"] = hd
    n_with = sum(1 for v in hd.values() if any(k.startswith("scope12_tCO2e") for k in v))
    task.log(f"{len(hd)} firm-years, {n_with} with scope 1+2")
    return {"firm_years": len(hd), "with_scope12": n_with}


AGENT = AgentDefinition(
    id="collect_hard_data", kind="collect_hard_data", name="Collect hard data",
    role="Fact collector",
    description="Extracted scope 1+2 (last 4 reported years), revenue and assurance flags per firm-year: self-reported figures from the firm's HKEX reports or the TWSE/TPEx open data. Timing rule: year t is known from the report published in t+1.",
    tools=("firm_hard_data", "read_processed"),
    inputs=("ctx.documents",), outputs=("ctx.hard_data",),
    run=run,
)
