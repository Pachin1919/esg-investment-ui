"""Portfolio recommendations from three inputs: current holdings, risk preference, green preference.

The user states their current portfolio (capital per asset), a risk preference and a green
preference, each on a 1-5 score. The scores map to outcome anchors — a target annual
volatility and a target greenness percentile of the candidate universe:

    risk  1 (cautious) .. 5 (aggressive)  ->  target ann. vol 8, 12, 15, 20, 25 %
    green 1 (indifferent) .. 5 (deep)     ->  portfolio average greenness at the 50th (no
                                              tilt), 60th, 70th, 80th, 90th percentile

Both appetites are anchored to outcomes, so "medium risk" and "quite green" mean the same
portfolio in every market: gamma is solved by bisection for the vol target and the green
target is enforced as a portfolio constraint (`optimize.mean_variance_green_targets`). When
too few firms have greenness to anchor on, the green tilt falls back to the GREEN_LAM table. Expected returns and covariance come from the
FF5+MOM+GMB factor model (mu = B mu_f, Sigma = B F B' + D), so recommendations are
Fama-French-consistent rather than driven by noisy sample moments. A linear turnover penalty
kappa * sum|w - w0| keeps the current portfolio as the default: a trade only happens if it
improves utility more than kappa. Holdings without estimated betas cannot be risk-modeled;
they are frozen at their current weight and reported under `unmodeled`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.portfolio.optimize import (
    factor_cov,
    factor_expected_returns,
    mean_variance_green_target_vol,
    mean_variance_green_targets,
)

RISK_VOL = {1: 0.08, 2: 0.12, 3: 0.15, 4: 0.20, 5: 0.25}
GREEN_PCTL = {1: None, 2: 0.60, 3: 0.70, 4: 0.80, 5: 0.90}
GREEN_LAM = {1: 0.0, 2: 0.25, 3: 0.5, 4: 1.0, 5: 2.0}  # fallback when greenness can't anchor


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
    b = betas.reindex(w.index)
    held = w[w > 1e-4]
    return {
        "ann_ret": float(12 * w @ m),
        "ann_vol": float(np.sqrt(max(12 * w @ S @ w, 0.0))),
        "g_avg": g_avg,
        "b_gmb": float((w * bg.fillna(0.0)).sum()) if bg.notna().any() else None,
        # weighted factor betas (mkt_rf, smb, hml, rmw, cma, mom, gmb when estimated)
        "exposures": {c[2:]: float((w * b[c].fillna(0.0)).sum())
                      for c in b.columns if c.startswith("b_") and b[c].notna().any()},
        "n_positions": len(held),
        "top_weight": float(held.max()) if len(held) else 0.0,
        "effective_n": float(1.0 / (held / held.sum()).pow(2).sum()) if len(held) else 0.0,
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
    max_new_capital: float = 0.0,
    vol_target: float | None = None,
    g_target: float | None = None,
    w_max: float = 0.15,
    min_trade: float = 0.005,
    universe: list[str] | None = None,
    keep_outside: bool = False,
) -> dict:
    """Trade list that moves the current portfolio toward the target risk/green profile.

    `holdings`: ticker -> capital. `betas`: per-firm factor betas indexed by firm_id (from
    `exposure_snapshot` / latest `green_exposures`). `g`: latest greenness per firm. `kappa`
    is the utility cost per unit one-way turnover: the green-term gradient is O(lam * z) ~ 1,
    so kappa 0.01-0.1 is the meaningful range. `max_new_capital`: the investor's upper limit
    on fresh capital to inject (e.g. 20000.0); the target portfolio is sized to current
    capital plus this budget and the trade list deploys it as net buys — the required
    injection never exceeds it. `vol_target`: explicit annualized volatility target (0.15 =
    15%); when omitted it is derived from `risk_score` via RISK_VOL. `g_target`: explicit
    greenness percentile in (0, 1); when omitted it is derived from `green_score` via
    GREEN_PCTL (score 1 = no tilt). `universe`: candidate
    subset from the preference screen (`screen.screen_universe`); holdings outside it are
    recommended for sale ("sell (outside preferences)"), holdings without betas stay frozen.
    `keep_outside`: holdings outside `universe` are left untouched instead ("hold (outside
    filter)") — the universe then only restricts what is bought and rebalanced; like the
    unmodeled ones they are outside the optimized sleeve, but they count in the before/after stats.
    Returns weights, trades, before/after stats and the unmodeled list."""
    lam = _score(green_score, GREEN_LAM, "green_score")  # fallback when the anchor is unusable
    if g_target is not None and not 0 < g_target < 1:
        raise ValueError(f"g_target is a percentile and must be in (0, 1), got {g_target}")
    g_pctl = GREEN_PCTL[int(green_score)] if g_target is None else g_target
    if vol_target is None:
        vol_target = _score(risk_score, RISK_VOL, "risk_score")
    elif vol_target <= 0:
        raise ValueError(f"vol_target must be positive, got {vol_target}")
    h = pd.Series(holdings, dtype=float).dropna()
    if (h < 0).any() or h.sum() <= 0:
        raise ValueError("holdings must be non-negative with positive total capital")
    if max_new_capital < 0:
        raise ValueError("max_new_capital must be >= 0")
    total = float(h.sum())
    target_total = total + float(max_new_capital)

    all_names = betas.index
    candidates = all_names.intersection(pd.Index(universe)) if universe is not None else all_names
    if len(candidates) == 0:
        raise ValueError("the preference filter leaves no candidate assets")
    unmodeled = h.index.difference(all_names)
    outside_pref = h.index.intersection(all_names).difference(candidates)
    kept = outside_pref if keep_outside else outside_pref[:0]
    w_frozen = float((h[unmodeled].sum() + h[kept].sum()) / target_total)
    if w_frozen >= 1.0:
        raise ValueError("none of the holdings have estimated betas; nothing to optimize")

    sub = betas.loc[candidates]
    w0c = pd.Series(0.0, index=candidates)
    w0c[h.index.intersection(candidates)] = h[h.index.intersection(candidates)] / target_total
    mu = factor_expected_returns(sub, f_mean)
    cov = factor_cov(sub, f_cov, idio_var)
    g_cand = g.reindex(candidates).dropna()
    anchor = g_pctl is not None and len(g_cand) >= 2 and g_cand.std(ddof=0) > 0
    if anchor:
        w, gamma, lam = mean_variance_green_targets(mu, cov, g=g, vol_target=vol_target,
                                                    g_target=float(g_cand.quantile(g_pctl)), lam0=0.0,
                                                    w_max=w_max, w0=w0c, kappa=kappa, w_sum=1.0 - w_frozen)
    else:
        w, gamma = mean_variance_green_target_vol(mu, cov, g=g, lam=lam, vol_target=vol_target,
                                                  w_max=w_max, w0=w0c, kappa=kappa, w_sum=1.0 - w_frozen)

    w0_full = pd.Series(0.0, index=all_names)
    w0_full[h.index.intersection(all_names)] = h[h.index.intersection(all_names)] / target_total
    w_full = pd.Series(0.0, index=all_names)
    w_full[candidates] = w
    w_full[kept] = h[kept] / target_total
    w_modeled = w_full.copy()  # every holding with betas, kept ones included
    frozen = h[unmodeled] / target_total
    w0_full = pd.concat([w0_full, frozen])
    w_full = pd.concat([w_full, frozen])
    trades = pd.DataFrame({
        "firm_id": w_full.index,
        "w_current": w0_full.values,
        "w_target": w_full.values,
        "dw": (w_full - w0_full).values,
    })
    trades["capital_delta"] = trades["dw"] * target_total
    trades["side"] = np.where(trades["dw"] > min_trade, "buy",
                              np.where(trades["dw"] < -min_trade, "sell", "hold"))
    trades.loc[trades["firm_id"].isin(unmodeled), "side"] = "frozen (unmodeled)"
    trades.loc[trades["firm_id"].isin(outside_pref), "side"] = (
        "hold (outside filter)" if keep_outside else "sell (outside preferences)")
    trades = trades.sort_values("dw", ascending=False).reset_index(drop=True)
    # stats cover every modeled holding, so before and after describe the same portfolio
    mu_all, cov_all = factor_expected_returns(betas, f_mean), factor_cov(betas, f_cov, idio_var)
    w0_current = pd.Series(0.0, index=all_names)
    w0_current[h.index.intersection(all_names)] = h[h.index.intersection(all_names)] / total
    return {
        "params": {"risk_score": int(risk_score), "green_score": int(green_score),
                   "gamma": gamma, "lam": lam, "kappa": kappa, "w_max": w_max,
                   "vol_target_ann": float(vol_target),
                   "g_target_pctl": float(g_pctl) if anchor else None,
                   "n_candidates": len(candidates)},
        "total_capital": total,
        "new_capital": float(max_new_capital),
        "target_capital": target_total,
        "weights": w,
        "trades": trades,
        "before": _stats(w0_current, mu_all, cov_all, g, betas),
        "after": _stats(w_modeled, mu_all, cov_all, g, betas),
        "turnover": float(0.5 * trades["dw"].abs().sum()),
        "unmodeled": [{"firm_id": f, "capital": float(h[f]), "weight": float(h[f] / total)}
                      for f in unmodeled],
    }
