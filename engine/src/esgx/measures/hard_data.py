"""HARD DATA block for a firm-year: the emissions and revenue figures the text is checked against.

Hong Kong / China (HKEX-listed): scope 1 + 2 extracted from the firm's own HKEX annual / ESG
reports (`emissions_hk.parquet`), with the third-party assurance flag; revenue from yfinance.
Taiwan: scope 1 + 2 from the TWSE / TPEx open ESG data, with verification flags; revenue
annualised from the exchanges' monthly filings. The `PROVENANCE` strings are what the scoring
prompt states as the source of the numbers — they matter, because the rubric weighs registry
or audited data differently from self-reported figures.
"""

from __future__ import annotations

import pandas as pd

from esgx.config import PROCESSED_DIR, RAW_DIR

PROVENANCE = {
    "hk": "scope 1+2 extracted from the firm's own HKEX annual / ESG reports (self-reported under HKEX Appendix C2 KPI A1.2; assurance flag where present), revenue from yfinance",
    "tw": "scope 1+2 from the TWSE / TPEx open ESG data (self-reported to the exchange; verification flags where present), revenue annualised from monthly exchange filings",
}

_NO_DATA = {
    "hk": "no emissions extracted from this firm's HKEX reports for the period",
    "tw": "this firm is not in the TWSE / TPEx open ESG data for the period",
}


def _hk_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    em = pd.DataFrame()
    p = PROCESSED_DIR / "emissions_hk.parquet"
    if p.exists():
        em = pd.read_parquet(p)
    parts = []
    for name in ("fundamentals_yf_hsci.parquet", "fundamentals_yf_hk.parquet"):
        f = RAW_DIR / name
        if f.exists():
            parts.append(pd.read_parquet(f))
    fu = pd.concat(parts, ignore_index=True).drop_duplicates(["firm_id", "year"]) if parts else pd.DataFrame()
    return em, fu


def _tw_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    from esgx.ingest.twse_esg import load_emissions_tw, load_fundamentals_tw

    return load_emissions_tw(), load_fundamentals_tw()


def hard_data_for(firm_id: str, year: int, market: str = "hk") -> dict:
    """Scope 1+2 trend (last 4 reported years up to `year`), revenue and assurance for one firm."""
    if market not in PROVENANCE:
        raise ValueError(f"market must be one of {sorted(PROVENANCE)}, got {market!r}")
    em, fu = _hk_frames() if market == "hk" else _tw_frames()
    if em.empty:
        return {"note": _NO_DATA[market]}
    em = em[(em["firm_id"] == firm_id) & em["matched"]].sort_values("year")
    if em.empty:
        return {"note": _NO_DATA[market]}
    recent = em[em["year"] <= year].tail(4)
    out: dict = {}
    verified = recent["verified"].astype(str) if "verified" in recent else None
    for i, r in enumerate(recent.itertuples()):
        s12 = (r.scope1 if pd.notna(r.scope1) else 0) + (r.scope2 if pd.notna(r.scope2) else 0)
        out[f"scope12_tCO2e_{int(r.year)}"] = round(float(s12))
        if verified is not None:
            out[f"third_party_assured_{int(r.year)}"] = verified.iloc[i]
    if not fu.empty:
        fu = fu[(fu["firm_id"] == firm_id) & fu["year"].isin(recent["year"])]
        for r in fu.itertuples():
            if pd.notna(r.revenue):
                out[f"revenue_musd_{int(r.year)}"] = round(float(r.revenue))
    if len(recent) >= 2:
        first, last = recent.iloc[0], recent.iloc[-1]
        s_first = (first.scope1 if pd.notna(first.scope1) else 0) + (first.scope2 if pd.notna(first.scope2) else 0)
        s_last = (last.scope1 if pd.notna(last.scope1) else 0) + (last.scope2 if pd.notna(last.scope2) else 0)
        out["scope12_change_pct"] = round(100 * (s_last / s_first - 1), 1) if s_first > 0 else None
    return out
