"""Time-series factor regressions: alpha of a return series on FF5 + MOM (+ GMB)."""

from __future__ import annotations

import pandas as pd
import statsmodels.api as sm

FF5_MOM = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]


def alpha_regression(series: pd.DataFrame, factors: pd.DataFrame, y: str, xs: list[str], nw_lags: int = 6) -> pd.Series:
    """series: month + y column. Returns alpha (monthly, decimal), t-stat, betas, R2, n."""
    df = series.merge(factors, on="month", how="inner").dropna(subset=[y] + xs)
    X = sm.add_constant(df[xs].astype(float))
    fit = sm.OLS(df[y].astype(float), X).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags})
    out = {"alpha": fit.params["const"], "t_alpha": fit.tvalues["const"], "r2": fit.rsquared, "n": int(fit.nobs)}
    out["idio_var"] = float(fit.resid.var(ddof=len(xs) + 1))  # residual variance, D in the factor-model Sigma
    for x in xs:
        out[f"b_{x}"] = fit.params[x]
    return pd.Series(out)
