"""Greenness à la Pástor, Stambaugh & Taylor (2022, "Dissecting Green Returns").

    g_i = -(10 - E_score_i) * E_weight_i / 100

E_score in [0,10] (10 = perfectly green), E_weight in [0,100] = importance of the
E pillar for the firm's industry. Perfectly green firms get g = 0; brown firms
get very negative g. Example from the lecture: a firm with (4.2, 48) -> -2.78,
a firm with (4.1, 11) -> -0.65.

The provider is `scores_from_walk` (returns the `esg_scores` table: firm_id, year, provider,
e_score, e_weight): E_score IS the deterministic walk score (`measures.walk_hard`, percentile
of emission intensity within industry and year), so the number that enters the greenwashing
flag and the number that enters greenness, GMB and the return tests are the same. E_weight is
the industry's aggregate intensity, ranked across industries. Firms without hard data have no
walk and therefore no greenness.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.schema import validate


def greenness(e_score: pd.Series | float, e_weight: pd.Series | float) -> pd.Series | float:
    return -(10.0 - e_score) * e_weight / 100.0


def industry_weight(df: pd.DataFrame, emissions_col: str, weight_range: tuple[float, float] = (5.0, 50.0)) -> pd.DataFrame:
    """E_weight per year and industry: aggregate intensity (sum emissions / sum revenue), percentile-ranked
    across industries each year and mapped to `weight_range`. `df` needs year, industry_grp, revenue."""
    ind = df.groupby(["year", "industry_grp"]).agg(em=(emissions_col, "sum"), rev=("revenue", "sum")).reset_index()
    ind["ind_int"] = ind["em"] / ind["rev"].where(ind["rev"] > 0)
    ind["ind_rank"] = ind.groupby("year")["ind_int"].rank(pct=True, method="average")
    lo, hi = weight_range
    ind["e_weight"] = lo + (hi - lo) * ind["ind_rank"]
    return ind[["year", "industry_grp", "e_weight"]]


def scores_from_walk(walk: pd.DataFrame, industry_col: str = "sector", weight_range: tuple[float, float] = (5.0, 50.0), provider: str = "walk_hard") -> pd.DataFrame:
    """`esg_scores` from the `walk_hard.walk_score` table: e_score = walk, e_weight from the
    industry's aggregate intensity. Revenue is recovered as level / intensity."""
    df = walk.dropna(subset=["walk", industry_col]).rename(columns={industry_col: "industry_grp"}).copy()
    df["revenue"] = df["level"] / df["intensity"].where(df["intensity"] > 0)
    df["revenue"] = df["revenue"].fillna(df.groupby(["year", "industry_grp"])["revenue"].transform("median"))  # zero-emission firms
    df = df.merge(industry_weight(df, "level", weight_range), on=["year", "industry_grp"], how="left")
    df["e_score"], df["provider"] = df["walk"], provider
    return validate(df[["firm_id", "year", "provider", "e_score", "e_weight"]].reset_index(drop=True), "esg_scores")


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
