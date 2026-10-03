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
) -> pd.Series:
    """Optimal weights indexed by firm_id. z(g) enters the objective only; firms without
    g get z = 0. Raises if the problem is infeasible (w_max * n < 1) or SLSQP fails."""
    names = mu.index
    n = len(names)
    if w_max * n < 1.0:
        raise ValueError(f"w_max={w_max} infeasible with {n} names (need w_max >= {1 / n:.3f})")
    S = cov.reindex(index=names, columns=names).to_numpy()
    m = mu.to_numpy(dtype=float)
    if g is not None:
        gg = g.reindex(names)
        z = ((gg - gg.mean()) / gg.std(ddof=0)).fillna(0.0).to_numpy()
    else:
        z = np.zeros(n)

    def neg_utility(w: np.ndarray) -> float:
        return float(-(w @ m - gamma / 2 * w @ S @ w + lam * w @ z))

    res = minimize(
        neg_utility,
        np.full(n, 1.0 / n),
        method="SLSQP",
        bounds=[(0.0, w_max)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
    )
    if not res.success:
        raise RuntimeError(f"mean_variance_green optimizer failed: {res.message}")
    return pd.Series(res.x, index=names)
