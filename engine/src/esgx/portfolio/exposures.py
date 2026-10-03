"""Per-asset green exposures: betas of stock returns on FF5 + MOM + GMB.

b_gmb is the asset's return sensitivity to the green factor — its *exposure*, as
opposed to its greenness characteristic g (how green the firm *is*). Positive b_gmb:
the stock gains when green outperforms, i.e. it hedges climate-concern shocks
(Pástor–Stambaugh–Taylor 2022). A firm can be brown (negative g) yet have positive
b_gmb; the tilt uses g, the risk model uses b_gmb.

Betas at month t are estimated on data up to t-1 (shifted, no look-ahead), same
convention as `factors.gmb.rolling_market_beta`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.factors.timeseries import FF5_MOM, alpha_regression


def _with_gmb(factors: pd.DataFrame, gmb: pd.DataFrame | None, gmb_col: str) -> pd.DataFrame:
    if gmb is None:
        return factors
    return factors.merge(gmb[["month", gmb_col]].rename(columns={gmb_col: "gmb"}), on="month", how="left")


def _rolling_betas(y: np.ndarray, X: np.ndarray, window: int, min_obs: int) -> np.ndarray:
    """Row t: OLS of y[max(0,t-window+1)..t] on [1, X[...]]. NaN until min_obs rows exist."""
    T = len(y)
    out = np.full((T, X.shape[1] + 1), np.nan)
    for t in range(min_obs - 1, T):
        lo = max(0, t - window + 1)
        Xi = np.column_stack([np.ones(t - lo + 1), X[lo : t + 1]])
        beta, *_ = np.linalg.lstsq(Xi, y[lo : t + 1], rcond=None)
        out[t] = beta
    return out


def green_exposures(
    panel: pd.DataFrame,
    factors: pd.DataFrame,
    gmb: pd.DataFrame | None = None,
    gmb_col: str = "gmb",
    xs: list[str] | None = None,
    window: int = 60,
    min_obs: int = 36,
) -> pd.DataFrame:
    """Rolling betas per firm. `panel`: firm x month with ret. Returns firm x month with
    alpha, b_<x> per factor and b_gmb (omitted when `gmb` is None); the first `min_obs`
    months per firm are NaN (warmup)."""
    xs = list(xs or FF5_MOM) + (["gmb"] if gmb is not None else [])
    fac = _with_gmb(factors, gmb, gmb_col)
    df = panel.merge(fac, on="month", how="left").sort_values(["firm_id", "month"])
    df["exret"] = df["ret"] - df["rf"]
    cols = ["alpha"] + [f"b_{x}" for x in xs]
    out = []
    for fid, gdf in df.groupby("firm_id"):
        sub = gdf.dropna(subset=["exret"] + xs)
        if len(sub) < min_obs:
            continue
        b = _rolling_betas(sub["exret"].to_numpy(), sub[xs].to_numpy(), window, min_obs)
        res = pd.DataFrame(b, columns=cols)
        res["firm_id"], res["month"] = fid, sub["month"].values
        out.append(res)
    if not out:
        return pd.DataFrame(columns=["firm_id", "month"] + cols)
    res = pd.concat(out, ignore_index=True).sort_values(["firm_id", "month"])
    res[cols] = res.groupby("firm_id")[cols].shift(1)  # betas at t use data up to t-1
    return res[["firm_id", "month"] + cols].reset_index(drop=True)


def exposure_snapshot(
    panel: pd.DataFrame,
    factors: pd.DataFrame,
    gmb: pd.DataFrame | None = None,
    gmb_col: str = "gmb",
    xs: list[str] | None = None,
    at: str | None = None,
    min_obs: int = 24,
) -> pd.DataFrame:
    """Full-sample (or ending at month `at`, e.g. "2025-12") betas per firm, via
    `factors.timeseries.alpha_regression`. Indexed by firm_id; columns alpha, t_alpha,
    r2, n, idio_var, b_<x>, b_gmb (b_gmb only when `gmb` is given)."""
    xs = list(xs or FF5_MOM) + (["gmb"] if gmb is not None else [])
    fac = _with_gmb(factors, gmb, gmb_col)
    df = panel.merge(fac[["month", "rf"]], on="month", how="left")
    df["exret"] = df["ret"] - df["rf"]
    if at is not None:
        df = df[df["month"] <= pd.Period(at, freq="M")]
    rows = {}
    for fid, gdf in df.groupby("firm_id"):
        if gdf["exret"].notna().sum() < min_obs:
            continue
        rows[fid] = alpha_regression(gdf[["month", "exret"]], fac, y="exret", xs=xs)
    return pd.DataFrame(rows).T.rename_axis("firm_id")
