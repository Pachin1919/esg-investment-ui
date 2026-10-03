"""Collector agent: fetches the source documents for each firm (deterministic, network only)."""

from __future__ import annotations

import pandas as pd

from pipeline.agents.base import AgentDefinition, StageTask


def run(task: StageTask) -> dict:
    firms = task.tools.load_universe(task.spec.universe).set_index("firm_id")
    wanted = set(task.param("sections") or [])
    frames = []
    for t in task.tickers:
        if t not in firms.index:
            task.log(f"skip {t}: not in universe")
            continue
        if task.spec.universe == "tw":
            task.log(f"skip {t}: Taiwan has no text source wired in yet (walk scores only)")
            continue
        docs = task.tools.hkex_report_documents(t, int(firms.loc[t, "stock_code"]), int(firms.loc[t, "hkex_sid"]), start=task.spec.start)
        if wanted and "section" in docs:
            docs = docs[docs["section"].isin(wanted)]
        docs["firm_name"] = firms.loc[t, "name"]
        frames.append(docs)
        task.log(f"{t}: {len(docs)} picked reports ({docs['accession'].nunique() if 'accession' in docs and len(docs) else 0} urls)")
    task.ctx["documents"] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return {"sections": len(task.ctx["documents"])}


AGENT = AgentDefinition(
    id="collect_documents", kind="collect_documents", name="Collect reports",
    role="Collector",
    description="HKEX annual and ESG reports per firm (Hang Seng universe, incl. HKEX-listed mainland China), one picked report per firm-year as full text. PDFs cached under data/raw.",
    tools=("load_universe", "hkex_list_reports", "hkex_fetch_pdf", "hkex_pdf_pages", "hkex_load_documents", "hkex_report_documents", "http_get", "html_to_text"),
    inputs=("tickers", "spec.universe", "spec.forms", "spec.start"), outputs=("ctx.documents",),
    default_params={"sections": ["full_report"]},
    run=run,
)
