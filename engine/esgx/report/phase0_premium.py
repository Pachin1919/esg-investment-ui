"""Phase 0: carbon premium via lagged Fama-MacBeth with the robustness matrix, plus caveats."""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.factors.famamacbeth import annual_returns, fama_macbeth
from esgx.report.md import md_table

SUPER_EMITTER_SECTORS = {"Utilities", "Energy"}


def build_carbon_premium(report: list[str], prices: pd.DataFrame, inten: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """Four Fama-MacBeth specifications (level / intensity, matched / ex super emitters / full universe)."""
    # ---------- carbon premium: lagged Fama-MacBeth ----------
    ar = annual_returns(prices)
    lag = inten.rename(columns={"year": "year_em"}).assign(year=lambda d: d["year_em"] + 1)  # year-t return on year t-1 emissions
    fm_panel = ar.merge(lag, on=["firm_id", "year"], how="inner").merge(firms[["firm_id", "sector"]], on="firm_id")
    fm_panel["log_size"] = np.log(fm_panel["mktcap_end"])
    fm_panel = fm_panel.dropna(subset=["log_size"])
    prev = ar.rename(columns={"ret_annual": "ret_prev"}).assign(year=lambda d: d["year"] + 1)[["firm_id", "year", "ret_prev"]]
    fm_panel = fm_panel.merge(prev, on=["firm_id", "year"], how="left")
    fm_panel = pd.concat([fm_panel, pd.get_dummies(fm_panel["sector"], prefix="sec", drop_first=True, dtype=float)], axis=1)
    sec_cols = [c for c in fm_panel.columns if c.startswith("sec_")]
    
    specs = {
        "log level, matched only": (fm_panel[fm_panel["matched"]], "log_level"),
        "log intensity, matched only": (fm_panel[fm_panel["matched"]], "log_intensity"),
        "log intensity, matched, ex super emitters": (fm_panel[fm_panel["matched"] & ~fm_panel["sector"].isin(SUPER_EMITTER_SECTORS)], "log_intensity"),
        "log intensity, full universe (unmatched=0)": (fm_panel.assign(log_intensity=fm_panel["log_intensity"].where(fm_panel["matched"], 0.0)), "log_intensity"),
    }
    rows = []
    for name, (pnl, xvar) in specs.items():
        try:
            tab = fama_macbeth(pnl, y="ret_annual", xs=[xvar, "log_size", "ret_prev"] + sec_cols, time_col="year", min_n=25)
            rows.append({"spec": name, "coef": tab.loc[xvar, "coef"], "t_nw": tab.loc[xvar, "t_nw"], "years": int(tab.loc[xvar, "n_periods"]), "avg_n": tab.loc[xvar, "avg_n"]})
        except ValueError as e:
            rows.append({"spec": name, "coef": np.nan, "t_nw": np.nan, "years": 0, "avg_n": np.nan, "note": str(e)})
    fmtab = pd.DataFrame(rows).set_index("spec")
    report.append("## Carbon premium: annual return on lagged emissions (Fama–MacBeth, NW t), controls log size, past return, sector dummies\n")
    report.append("BK 2021: positive premium on log *level* and growth, insignificant on intensity. Crosignani et al. 2025: positive on lagged intensity, negative for power generation, null for very large firms.\n")
    report.append(md_table(fmtab, "{:.3f}") + "\n")
    
    report.append("## Caveats\n")
    report.append(
        "- Greenness here is a *proxy* built from EPA GHGRP scope‑1 facility data (US, >25 kt/yr) and SEC revenue; it is not MSCI's E score. Firms without matched facilities are treated as the cleanest in their sector, which is wrong for name‑match failures.\n"
        "- Universe is the current S&P 500 (survivorship bias). Market caps use yfinance share histories, flat where missing.\n"
        "- Emissions for year t are applied from July t+1 (18‑month lag)."
    )
    return fmtab
