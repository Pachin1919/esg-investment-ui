"""Deterministic walk score from hard data only (no text, no LLM).

Walk = what the firm demonstrably does, measured on registry emissions and audited financials.
Components, each mapped to 0-10 by percentile rank within industry and year (10 = greenest):

* ``intensity_level`` : scope-1 intensity, tCO2e per USD million revenue (low = green).
  Crosignani, Osambela & Pritsker (2025) price intensity; Pástor, Stambaugh & Taylor (2022)
  rank environmental performance within industry.
* ``intensity_trend`` : one-year change in log intensity (falling = green); consecutive years only.
* ``emission_trend``  : one-year change in log scope-1 level (falling = green).
  Bolton & Kacperczyk (2021) show level and growth carry the premium, so both trends are kept.

``walk`` is the intensity-level component alone. No paper blends level and trend into one number
(Bolton & Kacperczyk keep them as separate regressors and get different results; Crosignani et al.
model intensity as a random walk, so a one-year change is mostly noise and moves with revenue,
e.g. oil prices). The two trend components are reported as their own columns, and
``walk_composite`` (weighted mean of the components that exist, weights renormalised) is kept
only as a sensitivity variant. Only firms with registry-matched emissions are scored: an
unmatched firm has no hard data and gets no walk score rather than a favourable one. Industries with fewer than ``min_group`` scored firms in a year are ranked across
the whole year instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WALK_WEIGHTS = {"intensity_level": 0.5, "intensity_trend": 0.3, "emission_trend": 0.2}
COMPONENT_SOURCE = {"intensity_level": "intensity", "intensity_trend": "d_log_intensity", "emission_trend": "d_log_level"}


def pct_score(x: pd.Series, groups: list[pd.Series], lower_is_greener: bool = True) -> pd.Series:
    """0-10 score from the percentile rank within groups; a single-member group scores 5."""
    g = x.groupby(groups)
    n = g.transform("count")
    r = (g.rank(method="average") - 1) / (n - 1).where(n > 1)
    r = r.where(n > 1, 0.5).where(x.notna())
    return 10.0 * (1.0 - r) if lower_is_greener else 10.0 * r


def walk_components(carbon: pd.DataFrame, firms: pd.DataFrame, industry_col: str = "sector", min_group: int = 5) -> pd.DataFrame:
    """carbon: output of `measures.carbon.carbon_intensity`. Returns firm × year component scores."""
    df = carbon[carbon["matched"] & carbon["intensity"].notna()].copy()
    df = df.merge(firms[["firm_id", industry_col]].drop_duplicates("firm_id"), on="firm_id", how="left").sort_values(["firm_id", "year"])
    # true log changes (relative), not the log1p columns of carbon_intensity, which turn into
    # absolute changes for low-intensity firms; consecutive years only
    g = df.groupby("firm_id")
    consecutive = g["year"].diff() == 1
    for src, out in (("intensity", "d_log_intensity"), ("level", "d_log_level")):
        logx = np.log(df[src].where(df[src] > 0))
        df[out] = logx.groupby(df["firm_id"]).diff().where(consecutive)
    size = df.groupby(["year", industry_col])["firm_id"].transform("count")
    df["rank_group"] = np.where(size >= min_group, df[industry_col], "_all")
    for comp, src in COMPONENT_SOURCE.items():
        df[f"walk_{comp}"] = pct_score(df[src], [df["year"], df["rank_group"]])
    return df


def walk_score(carbon: pd.DataFrame, firms: pd.DataFrame, weights: dict[str, float] | None = None, industry_col: str = "sector", min_group: int = 5) -> pd.DataFrame:
    """firm × year: walk (= intensity level, 0-10), the trend components, walk_composite and raw inputs."""
    w = weights or WALK_WEIGHTS
    df = walk_components(carbon, firms, industry_col, min_group)
    cols = [f"walk_{c}" for c in w]
    vals = df[cols].to_numpy(dtype=float)
    wts = np.where(~np.isnan(vals), np.array(list(w.values()))[None, :], 0.0)
    denom = wts.sum(axis=1)
    df["walk_composite"] = np.where(denom > 0, np.nansum(vals * wts, axis=1) / np.where(denom > 0, denom, 1), np.nan)
    df["walk"] = df["walk_intensity_level"]
    df["walk_n_components"] = (~np.isnan(vals)).sum(axis=1)
    keep = ["firm_id", "year", industry_col, "rank_group", "level", "intensity", "d_log_intensity", "d_log_level", *cols, "walk_n_components", "walk_composite", "walk"]
    return df[keep].reset_index(drop=True)
