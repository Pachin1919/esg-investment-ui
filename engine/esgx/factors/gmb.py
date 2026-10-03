"""Green-minus-brown factor, two ways (Pástor–Stambaugh–Taylor 2022).

1. `gmb_sorted`: value-weighted top-third-g minus bottom-third-g portfolio, rebalanced monthly.
2. `gmb_regression`: monthly cross-sectional regression of market-adjusted excess
   returns on g with no intercept:  f_t = (g'g)^{-1} g' alpha_t,
   alpha_t = r~_t - beta_{m,t-1} * r~_mt, betas from a rolling window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.measures.greenness import tercile_labels


def _vw(ret: pd.Series, w: pd.Series) -> float:
    w = w.fillna(0.0)
    if w.sum() <= 0:
        return float(ret.mean())
    return float(np.average(ret, weights=w))


def gmb_sorted(panel: pd.DataFrame, g_col: str = "g", weight: str = "vw") -> pd.DataFrame:
    """panel: firm × month with ret, mktcap, g. Returns month, green, brown, gmb, n."""
    rows = []
    for m, grp in panel.dropna(subset=[g_col, "ret"]).groupby("month"):
        if len(grp) < 30:
            continue
        lab = tercile_labels(grp[g_col])
        gr, br = grp[lab == "green"], grp[lab == "brown"]
        if weight == "vw":
            g_ret, b_ret = _vw(gr["ret"], gr["mktcap"]), _vw(br["ret"], br["mktcap"])
        else:
            g_ret, b_ret = float(gr["ret"].mean()), float(br["ret"].mean())
        rows.append({"month": m, "green": g_ret, "brown": b_ret, "gmb": g_ret - b_ret, "n": len(grp)})
    return pd.DataFrame(rows)


def rolling_market_beta(panel: pd.DataFrame, factors: pd.DataFrame, window: int = 60, min_obs: int = 24) -> pd.DataFrame:
    """Firm × month market beta from a trailing window ending at t-1 (no look-ahead)."""
    df = panel.merge(factors[["month", "mkt_rf", "rf"]], on="month", how="left")
    df["exret"] = df["ret"] - df["rf"]
    df = df.sort_values(["firm_id", "month"])
    out = []
    for fid, g in df.groupby("firm_id"):
        y, x = g["exret"], g["mkt_rf"]
        cov = y.rolling(window, min_periods=min_obs).cov(x)
        var = x.rolling(window, min_periods=min_obs).var()
        beta = (cov / var).shift(1)  # use info up to t-1
        out.append(pd.DataFrame({"firm_id": fid, "month": g["month"].values, "beta_m": beta.values}))
    return pd.concat(out, ignore_index=True)


def gmb_regression(panel: pd.DataFrame, factors: pd.DataFrame, g_col: str = "g", window: int = 60) -> pd.DataFrame:
    betas = rolling_market_beta(panel, factors, window=window)
    df = panel.merge(betas, on=["firm_id", "month"], how="left").merge(
        factors[["month", "mkt_rf", "rf"]], on="month", how="left"
    )
    df["alpha"] = (df["ret"] - df["rf"]) - df["beta_m"] * df["mkt_rf"]
    rows = []
    for m, grp in df.dropna(subset=["alpha", g_col]).groupby("month"):
        if len(grp) < 30:
            continue
        g = grp[g_col].to_numpy()
        a = grp["alpha"].to_numpy()
        f = float(g @ a / (g @ g)) if g @ g > 0 else np.nan
        rows.append({"month": m, "gmb_reg": f, "n": len(grp)})
    return pd.DataFrame(rows)


def cumulative(series: pd.Series) -> pd.Series:
    return (1.0 + series.fillna(0.0)).cumprod() - 1.0
