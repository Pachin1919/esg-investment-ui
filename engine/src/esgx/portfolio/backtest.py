"""Weight-panel backtest and portfolio characterization.

Convention: weights dated month t earn month-t returns. Turnover is one-way,
0.5 * sum |w_t - w_{t-1}| on the union of names, with drift ignored (transparent
rather than precise); cost = cost_bps * turnover. The initial build counts as turnover.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.factors.timeseries import FF5_MOM, alpha_regression


def backtest(weights: pd.DataFrame, panel: pd.DataFrame, cost_bps: float = 10.0) -> pd.DataFrame:
    """`weights`: long format (month, firm_id, w) on rebalance dates; `panel`: firm x month
    with ret. Returns month x (ret_gross, turnover, cost, ret, n)."""
    df = weights.merge(panel[["firm_id", "month", "ret"]], on=["firm_id", "month"], how="left")
    rows = []
    prev: pd.Series | None = None
    for m, grp in df.groupby("month"):
        wv = grp.set_index("firm_id")["w"]
        gross = float((wv * grp.set_index("firm_id")["ret"].fillna(0.0)).sum())
        if prev is None:
            turn = 0.5 * float(wv.abs().sum())  # initial build
        else:
            both = pd.concat([wv, prev], axis=1).fillna(0.0)
            turn = 0.5 * float((both.iloc[:, 0] - both.iloc[:, 1]).abs().sum())
        cost = cost_bps / 1e4 * turn
        rows.append({"month": m, "ret_gross": gross, "turnover": turn, "cost": cost,
                     "ret": gross - cost, "n": int((wv > 0).sum())})
        prev = wv
    return pd.DataFrame(rows)


def characterize(
    port_ret: pd.DataFrame,
    factors: pd.DataFrame,
    bench_ret: pd.DataFrame | None = None,
    gmb: pd.DataFrame | None = None,
    gmb_col: str = "gmb",
    nw_lags: int = 6,
) -> pd.Series:
    """The demo table for a return series (month, ret): annualized return/vol, Sharpe,
    FF5+MOM(+GMB) alpha with Newey-West t-stat and the portfolio's b_gmb; TE/IR/annualized
    active return vs `bench_ret` (month, ret) when given."""
    r = port_ret["ret"].astype(float)
    n = len(r)
    out = {
        "ann_ret": float((1 + r).prod() ** (12 / n) - 1),
        "ann_vol": float(r.std(ddof=1) * np.sqrt(12)),
        "n_months": n,
    }
    df = port_ret.merge(factors, on="month", how="left")
    df["exret"] = df["ret"] - df["rf"]
    out["sharpe"] = float(df["exret"].mean() / df["exret"].std(ddof=1) * np.sqrt(12))
    if bench_ret is not None:
        b = port_ret.merge(bench_ret.rename(columns={"ret": "r_bench"}), on="month", how="inner")
        active = b["ret"] - b["r_bench"]
        out["ann_active"] = float(active.mean() * 12)
        out["te"] = float(active.std(ddof=1) * np.sqrt(12))
        out["ir"] = float(active.mean() / active.std(ddof=1) * np.sqrt(12)) if active.std(ddof=1) > 0 else np.nan
    xs = list(FF5_MOM)
    fac = factors
    if gmb is not None:
        fac = factors.merge(gmb[["month", gmb_col]].rename(columns={gmb_col: "gmb"}), on="month", how="left")
        xs.append("gmb")
    a = alpha_regression(df[["month", "exret"]], fac, y="exret", xs=xs, nw_lags=nw_lags)
    out.update({k: float(v) for k, v in a.items()})
    return pd.Series(out)
