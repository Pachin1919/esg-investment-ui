"""Portfolio recommendations from three inputs: current holdings, risk preference, green preference.

The user states their current portfolio (capital per asset), a risk preference and a green
preference, each on a 1-5 score. The scores map to the optimizer's risk aversion (gamma)
and green tilt (lambda):

    risk  1 (cautious) .. 5 (aggressive)  ->  gamma 12, 8, 5, 3, 1.5
    green 1 (indifferent) .. 5 (deep)     ->  lam   0, 0.25, 0.5, 1, 2

Expected returns and covariance come from the FF5+MOM+GMB factor model (mu = B mu_f,
Sigma = B F B' + D), so recommendations are Fama-French-consistent rather than driven by
noisy sample moments. A linear turnover penalty kappa * sum|w - w0| keeps the current
portfolio as the default: a trade only happens if it improves utility more than kappa.
Holdings without estimated betas cannot be risk-modeled; they are frozen at their current
weight and reported under `unmodeled`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.portfolio.optimize import factor_cov, factor_expected_returns, mean_variance_green

RISK_GAMMA = {1: 12.0, 2: 8.0, 3: 5.0, 4: 3.0, 5: 1.5}
GREEN_LAM = {1: 0.0, 2: 0.25, 3: 0.5, 4: 1.0, 5: 2.0}


def _score(value: int, table: dict[int, float], name: str) -> float:
    try:
        return table[int(value)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"{name} must be an integer 1-5, got {value!r}") from None


def _stats(w: pd.Series, mu: pd.Series, cov: pd.DataFrame, g: pd.Series, betas: pd.DataFrame) -> dict:
    m = mu.reindex(w.index).fillna(0.0)
    S = cov.reindex(index=w.index, columns=w.index).fillna(0.0).to_numpy()
    gf = g.reindex(w.index)
    g_avg = float((w * gf).sum() / w[gf.notna()].sum()) if gf.notna().any() and w[gf.notna()].sum() > 0 else None
    bg = betas["b_gmb"].reindex(w.index) if "b_gmb" in betas.columns else pd.Series(np.nan, index=w.index)
    return {
        "ann_ret": float(12 * w @ m),
        "ann_vol": float(np.sqrt(max(12 * w @ S @ w, 0.0))),
        "g_avg": g_avg,
        "b_gmb": float((w * bg.fillna(0.0)).sum()) if bg.notna().any() else None,
    }


def recommend(
    holdings: dict[str, float] | pd.Series,
    betas: pd.DataFrame,
    g: pd.Series,
    f_mean: pd.Series,
    f_cov: pd.DataFrame,
    idio_var: pd.Series,
    risk_score: int = 3,
    green_score: int = 3,
    kappa: float = 0.02,
    w_max: float = 0.15,
    min_trade: float = 0.005,
    universe: list[str] | None = None,
) -> dict:
    """Trade list that moves the current portfolio toward the target risk/green profile.

    `holdings`: ticker -> capital. `betas`: per-firm factor betas indexed by firm_id (from
    `exposure_snapshot` / latest `green_exposures`). `g`: latest greenness per firm. `kappa`
    is the utility cost per unit one-way turnover: the green-term gradient is O(lam * z) ~ 1,
    so kappa 0.01-0.1 is the meaningful range. `universe`: candidate subset from the
    preference screen (`screen.screen_universe`); holdings outside it are recommended for
    sale ("sell (outside preferences)"), holdings without betas stay frozen. Returns
    weights, trades, before/after stats and the unmodeled list."""
    gamma = _score(risk_score, RISK_GAMMA, "risk_score")
    lam = _score(green_score, GREEN_LAM, "green_score")
    h = pd.Series(holdings, dtype=float).dropna()
    if (h < 0).any() or h.sum() <= 0:
        raise ValueError("holdings must be non-negative with positive total capital")
    total = float(h.sum())

    all_names = betas.index
    candidates = all_names.intersection(pd.Index(universe)) if universe is not None else all_names
    if len(candidates) == 0:
        raise ValueError("the preference filter leaves no candidate assets")
    unmodeled = h.index.difference(all_names)
    outside_pref = h.index.intersection(all_names).difference(candidates)
    w_frozen = float(h[unmodeled].sum() / total)
    if w_frozen >= 1.0:
        raise ValueError("none of the holdings have estimated betas; nothing to optimize")

    sub = betas.loc[candidates]
    w0c = pd.Series(0.0, index=candidates)
    w0c[h.index.intersection(candidates)] = h[h.index.intersection(candidates)] / total
    mu = factor_expected_returns(sub, f_mean)
    cov = factor_cov(sub, f_cov, idio_var)
    w = mean_variance_green(mu, cov, g=g, lam=lam, gamma=gamma, w_max=w_max,
                            w0=w0c, kappa=kappa, w_sum=1.0 - w_frozen)

    w0_full = pd.Series(0.0, index=all_names)
    w0_full[h.index.intersection(all_names)] = h[h.index.intersection(all_names)] / total
    w_full = pd.Series(0.0, index=all_names)
    w_full[candidates] = w
    frozen = h[unmodeled] / total
    w0_full = pd.concat([w0_full, frozen])
    w_full = pd.concat([w_full, frozen])
    trades = pd.DataFrame({
        "firm_id": w_full.index,
        "w_current": w0_full.values,
        "w_target": w_full.values,
        "dw": (w_full - w0_full).values,
    })
    trades["capital_delta"] = trades["dw"] * total
    trades["side"] = np.where(trades["dw"] > min_trade, "buy",
                              np.where(trades["dw"] < -min_trade, "sell", "hold"))
    trades.loc[trades["firm_id"].isin(unmodeled), "side"] = "frozen (unmodeled)"
    trades.loc[trades["firm_id"].isin(outside_pref), "side"] = "sell (outside preferences)"
    trades = trades.sort_values("dw", ascending=False).reset_index(drop=True)
    return {
        "params": {"risk_score": int(risk_score), "green_score": int(green_score),
                   "gamma": gamma, "lam": lam, "kappa": kappa, "w_max": w_max,
                   "n_candidates": len(candidates)},
        "total_capital": total,
        "weights": w,
        "trades": trades,
        "before": _stats(w0_full[w0_full.index.isin(all_names)], mu, cov, g, sub),
        "after": _stats(w, mu, cov, g, sub),
        "turnover": float(0.5 * trades["dw"].abs().sum()),
        "unmodeled": [{"firm_id": f, "capital": float(h[f]), "weight": float(h[f] / total)}
                      for f in unmodeled],
    }
