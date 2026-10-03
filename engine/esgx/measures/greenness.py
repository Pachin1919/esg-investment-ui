"""Greenness à la Pástor, Stambaugh & Taylor (2022, "Dissecting Green Returns").

    g_i = -(10 - E_score_i) * E_weight_i / 100

E_score in [0,10] (10 = perfectly green), E_weight in [0,100] = importance of the
E pillar for the firm's industry. Perfectly green firms get g = 0; brown firms
get very negative g. Example from the lecture: Exxon (4.2, 48) -> -2.78,
Best Buy (4.1, 11) -> -0.65.

Providers
---------
* `scores_from_provider`: use real E_score / E_weight (MSCI, Sustainalytics...) when available.
* `scores_from_carbon_intensity`: free proxy with the same structure –
  E_weight from the industry's median intensity rank, E_score from the firm's
  within-industry intensity rank. Unmatched (no GHGRP facility) firms are treated
  as the cleanest in their industry *only if* `unmatched_as_clean=True`; otherwise NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.schema import validate


def greenness(e_score: pd.Series | float, e_weight: pd.Series | float) -> pd.Series | float:
    return -(10.0 - e_score) * e_weight / 100.0


def scores_from_carbon_intensity(
    intensity_annual: pd.DataFrame,
    firms: pd.DataFrame,
    industry_col: str = "sector",
    unmatched_as_clean: bool = True,
    weight_range: tuple[float, float] = (5.0, 50.0),
) -> pd.DataFrame:
    """Build an `esg_scores` table (provider='carbon_proxy') from firm × year intensity."""
    df = intensity_annual.merge(firms[["firm_id", industry_col]], on="firm_id", how="left")
    df = df.rename(columns={industry_col: "industry_grp"})
    if "revenue" not in df.columns:
        df["revenue"] = 1.0
    df = df.dropna(subset=["revenue"])
    x = df["intensity"].copy()
    if unmatched_as_clean:
        x = x.where(df["matched"], 0.0)
    df["_x"] = x
    df = df.dropna(subset=["_x", "industry_grp"])

    # E_weight: industry aggregate intensity (sum emissions / sum revenue, unmatched = 0
    # emissions but real revenue), percentile-ranked across industries each year.
    df["_em"] = df["_x"] * df["revenue"]
    ind = df.groupby(["year", "industry_grp"]).agg(em=("_em", "sum"), rev=("revenue", "sum")).reset_index()
    ind["ind_int"] = ind["em"] / ind["rev"].where(ind["rev"] > 0)
    ind["ind_rank"] = ind.groupby("year")["ind_int"].rank(pct=True, method="average")
    lo, hi = weight_range
    ind["e_weight"] = lo + (hi - lo) * ind["ind_rank"]
    df = df.merge(ind[["year", "industry_grp", "e_weight"]], on=["year", "industry_grp"], how="left")

    # E_score: within-industry percentile of intensity (low intensity -> high score).
    # method="min" so all tied-at-zero firms sit at the clean end, not in the middle.
    n = df.groupby(["year", "industry_grp"])["_x"].transform("size")
    df["within_rank"] = df.groupby(["year", "industry_grp"])["_x"].rank(pct=False, method="min")
    df["e_score"] = (10.0 * (1.0 - (df["within_rank"] - 1) / n.clip(lower=1))).clip(0, 10)
    df["provider"] = "carbon_proxy"
    out = df[["firm_id", "year", "provider", "e_score", "e_weight"]].reset_index(drop=True)
    return validate(out, "esg_scores")


def greenness_table(esg_scores: pd.DataFrame, firms: pd.DataFrame, industry_col: str = "sector") -> pd.DataFrame:
    """firm × year greenness with across/within-industry decomposition (PST Section 5)."""
    df = esg_scores.copy()
    df["g"] = greenness(df["e_score"], df["e_weight"])
    df = df.merge(firms[["firm_id", industry_col]], on="firm_id", how="left")
    df["g_across"] = df.groupby(["year", industry_col])["g"].transform("mean")
    df["g_within"] = df["g"] - df["g_across"]
    return df[["firm_id", "year", "provider", "e_score", "e_weight", "g", "g_across", "g_within"]]


def tercile_labels(g: pd.Series) -> pd.Series:
    """'green' (top third of g), 'brown' (bottom third), 'mid'."""
    q = g.rank(pct=True, method="first")
    return pd.Series(np.where(q > 2 / 3, "green", np.where(q <= 1 / 3, "brown", "mid")), index=g.index)
