"""Fama–MacBeth (1973) cross-sectional regressions with Newey–West standard errors.

Used to estimate the carbon premium (Bolton–Kacperczyk 2021; Crosignani et al. 2025).
Lecture 3 warns: use the *lagged* specification (year t-1 emissions, year-t returns)
and annual returns; contemporaneous monthly specs are biased toward zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def fama_macbeth(
    panel: pd.DataFrame,
    y: str,
    xs: list[str],
    time_col: str = "year",
    nw_lags: int = 2,
    min_n: int = 30,
) -> pd.DataFrame:
    """Return coefficient table: mean, NW t-stat, n periods, avg cross-section size."""
    coefs, ns = [], []
    for t, grp in panel.dropna(subset=[y] + xs).groupby(time_col):
        if len(grp) < min_n:
            continue
        Xraw = grp[xs].astype(float)
        Xraw = Xraw.loc[:, Xraw.std() > 0]  # drop dummies that are constant in this cross-section
        X = sm.add_constant(Xraw)
        b = sm.OLS(grp[y].astype(float), X).fit().params
        b.name = t
        coefs.append(b)
        ns.append(len(grp))
    if not coefs:
        raise ValueError("no periods with enough observations")
    C = pd.DataFrame(coefs)
    rows = []
    for c in C.columns:
        s = C[c].dropna()
        ols = sm.OLS(s.values, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags})
        rows.append({"var": c, "coef": float(s.mean()), "t_nw": float(ols.tvalues[0]), "n_periods": len(s), "avg_n": float(np.mean(ns))})
    return pd.DataFrame(rows).set_index("var")


def annual_returns(prices_monthly: pd.DataFrame) -> pd.DataFrame:
    """Compound monthly returns to calendar-year returns; require >= 10 months."""
    df = prices_monthly.copy()
    df["year"] = df["month"].dt.year
    g = df.groupby(["firm_id", "year"])
    out = g["ret"].apply(lambda r: float(np.prod(1 + r) - 1)).rename("ret_annual").reset_index()
    out["n_months"] = g["ret"].size().values
    out = out[out["n_months"] >= 10]
    size = df.sort_values("month").groupby(["firm_id", "year"])["mktcap"].last().rename("mktcap_end").reset_index()
    return out.merge(size, on=["firm_id", "year"], how="left")
