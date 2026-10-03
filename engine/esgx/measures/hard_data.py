"""HARD DATA block for a firm-year: GHGRP scope 1 trend and revenue from the processed tables."""

from __future__ import annotations

import pandas as pd

from esgx.config import PROCESSED_DIR, RAW_DIR


def hard_data_for(firm_id: str, year: int) -> dict:
    """Scope-1 trend and intensity from the phase-0 tables, if present."""
    p = PROCESSED_DIR / "emissions.parquet"
    if not p.exists():
        return {}
    em = pd.read_parquet(p)
    em = em[(em["firm_id"] == firm_id) & em["matched"]].sort_values("year")
    if em.empty:
        return {"ghgrp_scope1": "no matched EPA GHGRP facilities (firm may be below the 25 kt threshold)"}
    recent = em[em["year"] <= year].tail(4)
    out = {f"scope1_tCO2e_{int(r.year)}": round(float(r.scope1)) for r in recent.itertuples()}
    f = RAW_DIR / "fundamentals.parquet"
    if f.exists():
        fu = pd.read_parquet(f)
        fu = fu[(fu["firm_id"] == firm_id) & fu["year"].isin(recent["year"])]
        for r in fu.itertuples():
            if pd.notna(r.revenue):
                out[f"revenue_musd_{int(r.year)}"] = round(float(r.revenue))
    if len(recent) >= 2:
        first, last = recent.iloc[0], recent.iloc[-1]
        out["scope1_change_pct"] = round(100 * (last.scope1 / first.scope1 - 1), 1) if first.scope1 > 0 else None
    return out
