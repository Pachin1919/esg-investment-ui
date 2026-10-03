"""Mean-variance allocation with a green term — the optional alternative to tilt.py.

    max_w  w'mu - gamma/2 * w'Σw + lam * w'z(g)   s.t.  1'w = 1, 0 <= w_i <= w_max

Σ comes from a factor model (B F B' + D) built on the FF5+MOM+GMB betas from
`portfolio.exposures`: with ~5 years of monthly HK history the sample covariance is
too noisy. mu comes from factor means via those same betas — sample mean returns are
not a usable mu (Merton 1980). SLSQP via scipy; no new dependency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _beta_frame(betas: pd.DataFrame) -> pd.DataFrame:
    """betas (indexed by firm_id) with columns b_<factor> -> columns <factor>."""
    cols = [c for c in betas.columns if c.startswith("b_")]
    return betas[cols].rename(columns={c: c[2:] for c in cols})


def factor_moments(factors: pd.DataFrame, cols: list[str]) -> tuple[pd.Series, pd.DataFrame]:
    """Mean and covariance of the factor return series (include gmb to use it in mu/Σ)."""
    df = factors[cols].astype(float).dropna()
    return df.mean(), df.cov()


def factor_expected_returns(betas: pd.DataFrame, f_mean: pd.Series) -> pd.Series:
    """mu_i = B_i' mu_f over the factor columns of `betas`. Indexed by firm_id."""
    B = _beta_frame(betas)
    return B @ f_mean.reindex(B.columns)


def factor_cov(betas: pd.DataFrame, f_cov: pd.DataFrame, idio_var: pd.Series) -> pd.DataFrame:
    """Σ = B F B' + D. `idio_var`: per-firm residual variance, indexed like `betas`."""
    B = _beta_frame(betas)
    F = f_cov.reindex(index=B.columns, columns=B.columns).to_numpy()
    Bv = B.to_numpy()
    S = Bv @ F @ Bv.T + np.diag(idio_var.reindex(betas.index).to_numpy())
    return pd.DataFrame(S, index=betas.index, columns=betas.index)


def mean_variance_green(
    mu: pd.Series,
    cov: pd.DataFrame,
    g: pd.Series | None = None,
    lam: float = 0.0,
    gamma: float = 5.0,
    w_max: float = 0.10,
    w0: pd.Series | None = None,
    kappa: float = 0.0,
    w_sum: float = 1.0,
    w_start: np.ndarray | None = None,
    g_floor: float | None = None,
) -> pd.Series:
    """Optimal weights indexed by firm_id, summing to `w_sum`. z(g) enters the objective
    only; firms without g get z = 0. With `w0` (current weights) and `kappa` (penalty per
    unit one-way turnover) the objective gains -kappa * sum|w - w0|, solved exactly via a
    buy/sell split — no-change is the default unless a trade earns its keep. `g_floor` adds
    a hard linear constraint: portfolio average greenness (over firms with a g value) must
    be at least g_floor — the anchored alternative to the lam tilt. `w_start` overrides the
    uniform starting point. Raises if the problem is infeasible (w_max * n < w_sum) or
    SLSQP fails."""
    names = mu.index
    n = len(names)
    if w_max * n < w_sum - 1e-12:
        raise ValueError(f"w_max={w_max} infeasible with {n} names (need w_max >= {w_sum / n:.3f})")
    S = cov.reindex(index=names, columns=names).to_numpy()
    m = mu.to_numpy(dtype=float)
    scale = max(1.0, gamma, abs(lam))  # identical argmin, but SLSQP linesearch stays scaled
    if g is not None:
        gg = g.reindex(names)
        z = ((gg - gg.mean()) / gg.std(ddof=0)).fillna(0.0).to_numpy()
    else:
        z = np.zeros(n)
    extra, extra_split = [], []
    if g_floor is not None and g is not None:
        valid = gg.notna().to_numpy()
        gvals = gg.to_numpy()
        extra = [{"type": "ineq", "fun": lambda w, v=valid, gv=gvals: w[v] @ gv[v] - g_floor * w[v].sum()}]
        extra_split = [{"type": "ineq", "fun": lambda x, v=valid, gv=gvals, n=n: x[:n][v] @ gv[v] - g_floor * x[:n][v].sum()}]

    if w0 is None or kappa <= 0.0:
        def neg_utility(w: np.ndarray) -> float:
            return float(-(w @ m - gamma / 2 * w @ S @ w + lam * w @ z) / scale)

        res = minimize(
            neg_utility,
            np.full(n, w_sum / n) if w_start is None else w_start,
            method="SLSQP",
            bounds=[(0.0, w_max)] * n,
            constraints=[{"type": "eq", "fun": lambda w: w.sum() - w_sum}] + extra,
        )
    else:
        w0v = w0.reindex(names).fillna(0.0).to_numpy()

        def neg_utility_split(x: np.ndarray) -> float:  # x = [w, d+, d-], w - w0 = d+ - d-
            w, dp, dm = x[:n], x[n : 2 * n], x[2 * n :]
            return float(-(w @ m - gamma / 2 * w @ S @ w + lam * w @ z) / scale + kappa / scale * (dp.sum() + dm.sum()))

        x0 = np.concatenate([np.full(n, w_sum / n) if w_start is None else w_start, np.zeros(2 * n)])
        res = minimize(
            neg_utility_split,
            x0,
            method="SLSQP",
            bounds=[(0.0, w_max)] * n + [(0.0, None)] * 2 * n,
            constraints=[
                {"type": "eq", "fun": lambda x: x[:n].sum() - w_sum},
                {"type": "eq", "fun": lambda x: x[:n] - w0v - x[n : 2 * n] + x[2 * n :]},
            ]
            + extra_split,
        )
        res.x = res.x[:n]
    if not res.success:
        raise RuntimeError(f"mean_variance_green optimizer failed: {res.message}")
    return pd.Series(res.x, index=names)


def mean_variance_green_target_vol(
    mu: pd.Series,
    cov: pd.DataFrame,
    g: pd.Series | None = None,
    lam: float = 0.0,
    vol_target: float = 0.15,
    tol: float = 0.002,
    max_iter: int = 24,
    **kwargs,
) -> tuple[pd.Series, float]:
    """mean_variance_green with gamma solved so the portfolio's annualized vol hits `vol_target`.

    Anchors the investor's risk appetite to an outcome (a yearly volatility they can feel)
    instead of an abstract risk-aversion coefficient: portfolio vol falls as gamma rises, so
    a bisection on gamma converges quickly. `vol_target` is annualized (0.15 = 15%). Outside
    the achievable range the nearest boundary is returned: below the floor the min-variance
    portfolio (largest gamma tried), above the ceiling the gamma ~ 0 portfolio. Extra kwargs
    (w_max, w0, kappa, w_sum) pass through to mean_variance_green. Returns (weights, gamma)."""
    if vol_target <= 0:
        raise ValueError(f"vol_target must be positive, got {vol_target}")

    def solve(gamma: float) -> tuple[pd.Series, float]:
        w = mean_variance_green(mu, cov, g=g, lam=lam, gamma=gamma, **kwargs)
        S = cov.reindex(index=w.index, columns=w.index).to_numpy()
        return w, float(np.sqrt(max(12.0 * w @ S @ w, 0.0)))

    w_ceiling, v_ceiling = solve(0.0)  # least risk-averse: the riskiest allowed portfolio
    if v_ceiling <= vol_target:
        return w_ceiling, 0.0
    lo, hi = 0.0, 8.0
    w_hi, v_hi = solve(hi)
    while v_hi > vol_target and hi < 1e3:  # expand until the floor is below the target
        lo, hi = hi, hi * 4
        w_hi, v_hi = solve(hi)
    if v_hi > vol_target:
        return w_hi, hi  # min-variance portfolio is still riskier than the target
    best_w, best_g = w_hi, hi
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        w_mid, v_mid = solve(mid)
        if abs(v_mid - vol_target) <= tol:
            return w_mid, mid
        if v_mid > vol_target:
            lo = mid
        else:
            hi, best_w, best_g = mid, w_mid, mid
    return best_w, best_g


def mean_variance_green_targets(
    mu: pd.Series,
    cov: pd.DataFrame,
    g: pd.Series,
    vol_target: float,
    g_target: float | None = None,
    lam0: float = 0.0,
    tol: float = 0.002,
    max_iter: int = 24,
    **kwargs,
) -> tuple[pd.Series, float, float | None]:
    """Solve mean_variance_green against two anchors: annualized volatility `vol_target`
    and portfolio average greenness `g_target` (in g units — e.g. a percentile of the
    universe's g, so 'green 4' can mean 'top 20% greenness').

    The green anchor is a hard linear constraint (average g >= g_target) rather than a lam
    tilt to bisect: the portfolio then sits exactly at the target when it binds, and only
    gamma is left to bisect for the vol target — no two-knob coordination problem. A
    g_target above the greenest allowed portfolio is clamped to that ceiling; a vol target
    below the floor the constraint imposes returns the calmest feasible portfolio. Portfolio
    average greenness uses only firms with a g value (NaN excluded), same convention as the
    response stats. Returns (weights, gamma, lam); lam is None on the anchored path because
    greenness comes from the constraint, not a tilt."""
    if g_target is None:
        w, gamma = mean_variance_green_target_vol(mu, cov, g=g, lam=lam0, vol_target=vol_target, **kwargs)
        return w, gamma, None
    gv = g.reindex(mu.index)

    def g_avg(w: pd.Series) -> float:
        valid = gv.notna().to_numpy()
        return float(w.to_numpy()[valid] @ gv.to_numpy()[valid] / w.to_numpy()[valid].sum()) if valid.any() and w.to_numpy()[valid].sum() > 0 else 0.0

    w_green = mean_variance_green(mu, cov, g=g, lam=1.0, gamma=0.0, **kwargs)  # greenest allowed
    g_eff = min(g_target, g_avg(w_green))

    def solve(gamma: float) -> tuple[pd.Series, float]:
        w = mean_variance_green(mu, cov, g=g, lam=0.0, gamma=gamma, g_floor=g_eff, **kwargs)
        S = cov.reindex(index=w.index, columns=w.index).to_numpy()
        return w, float(np.sqrt(max(12.0 * w @ S @ w, 0.0)))

    w_ceiling, v_ceiling = solve(0.0)
    if v_ceiling <= vol_target:
        return w_ceiling, 0.0, None
    lo, hi = 0.0, 8.0
    w_hi, v_hi = solve(hi)
    while v_hi > vol_target and hi < 1e3:  # expand until the floor is below the target
        lo, hi = hi, hi * 4
        w_hi, v_hi = solve(hi)
    if v_hi > vol_target:
        return w_hi, hi, None  # calmest portfolio under the green constraint is still riskier
    best_w, best_g = w_hi, hi
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        w_mid, v_mid = solve(mid)
        if abs(v_mid - vol_target) <= tol:
            return w_mid, mid, None
        if v_mid > vol_target:
            lo = mid
        else:
            hi, best_w, best_g = mid, w_mid, mid
    return best_w, best_g, None
