"""Predictive validation of talk and walk (Chen 2025, Section 5, eq. 1).

    outcome_{i,t+h} = β·walk_{i,t} + γ·talk_{i,t} + δ·controls_{i,t} + α_industry×year + ε

A walk measure is valid if β < 0 for next-year emissions (and > 0 for disclosure); a talk
measure must *not* predict emissions (γ ≈ 0). If talk predicts lower emissions, the text measure
is really a walk measure in disguise. Chen uses firm and industry × time fixed effects with
controls for size, book-to-market, leverage and ROA; here the panel is short (a few years per
firm), so firm fixed effects are not identified and we use industry × year effects plus log
revenue, with standard errors clustered by firm.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def emissions_outcomes(emissions: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
    """firm × year: log scope 1, log intensity and their one-year-ahead changes (matched rows only)."""
    em = emissions[emissions["matched"]].merge(fundamentals[["firm_id", "year", "revenue"]], on=["firm_id", "year"], how="left")
    em = em.sort_values(["firm_id", "year"])
    em["log_scope1"] = np.log1p(em["scope1"])
    em["log_intensity"] = np.log1p(em["scope1"] / em["revenue"].where(em["revenue"] > 0))
    em["log_revenue"] = np.log1p(em["revenue"])
    g = em.groupby("firm_id")
    em["d_log_scope1_next"] = g["log_scope1"].shift(-1) - em["log_scope1"]
    em["d_log_intensity_next"] = g["log_intensity"].shift(-1) - em["log_intensity"]
    return em[["firm_id", "year", "log_scope1", "log_intensity", "log_revenue", "d_log_scope1_next", "d_log_intensity_next"]]


def predictive_regression(
    firm_year: pd.DataFrame,
    outcomes: pd.DataFrame,
    outcome: str = "d_log_scope1_next",
    pillars: tuple[str, ...] = ("walk", "talk"),
    controls: tuple[str, ...] = ("log_revenue",),
    industry_col: str = "sector",
    min_obs: int = 20,
) -> pd.DataFrame:
    """Coefficient table (coef, t, p, n) for ``outcome`` on the pillars with industry × year effects.
    ``firm_year`` needs firm_id, year, the pillars and ``industry_col``."""
    df = firm_year.merge(outcomes, on=["firm_id", "year"], how="inner")
    cols = [outcome, *pillars, *controls]
    df = df.dropna(subset=cols)
    if len(df) < min_obs:
        raise ValueError(f"only {len(df)} observations with {outcome} and pillars; need {min_obs}")
    df["_fe"] = df[industry_col].astype(str) + "|" + df["year"].astype(str)
    X = pd.concat([df[list(pillars) + list(controls)].astype(float), pd.get_dummies(df["_fe"], drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    fit = sm.OLS(df[outcome].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df["firm_id"])[0]})
    rows = [{"var": v, "coef": float(fit.params[v]), "t": float(fit.tvalues[v]), "p": float(fit.pvalues[v]), "n": int(fit.nobs)}
            for v in [*pillars, *controls]]
    return pd.DataFrame(rows).set_index("var")


def validation_table(firm_year: pd.DataFrame, emissions: pd.DataFrame, fundamentals: pd.DataFrame, industry_col: str = "sector") -> pd.DataFrame:
    """Both outcomes (scope-1 change, intensity change) stacked: the table a paper would report."""
    oc = emissions_outcomes(emissions, fundamentals)
    parts = []
    for outcome in ("d_log_scope1_next", "d_log_intensity_next"):
        t = predictive_regression(firm_year, oc, outcome=outcome, industry_col=industry_col)
        t["outcome"] = outcome
        parts.append(t.reset_index())
    return pd.concat(parts, ignore_index=True).set_index(["outcome", "var"])
