"""Carbon exposure: levels, changes, intensity, and publication-lag alignment.

Lecture 3 lesson: unscaled emissions mostly measure firm size. Always report
intensity (tCO2e per USD million revenue) alongside levels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.config import EMISSIONS_PUBLICATION_LAG_MONTHS


def carbon_intensity(emissions: pd.DataFrame, fundamentals: pd.DataFrame, scope: str = "scope1") -> pd.DataFrame:
    """firm × year: emissions level, log level, intensity, and yoy change in log emissions."""
    df = emissions.merge(fundamentals[["firm_id", "year", "revenue"]], on=["firm_id", "year"], how="left")
    df = df.sort_values(["firm_id", "year"])
    df["level"] = df[scope]
    df["log_level"] = np.log1p(df["level"])
    df["intensity"] = df["level"] / df["revenue"].where(df["revenue"] > 0)
    df["log_intensity"] = np.log1p(df["intensity"])
    df["d_log_level"] = df.groupby("firm_id")["log_level"].diff()
    return df[["firm_id", "year", "matched", "level", "log_level", "intensity", "log_intensity", "d_log_level", "revenue"]]


def align_annual_to_months(annual: pd.DataFrame, months: pd.PeriodIndex, lag_months: int = EMISSIONS_PUBLICATION_LAG_MONTHS) -> pd.DataFrame:
    """Expand firm × year rows to firm × month, applying a publication lag.

    Year-t values become effective at (Dec t) + lag_months; the default seven
    months means July t+1. This fallback is an assumed availability convention.
    If available_date is supplied, use the following month to avoid using information
    published within a return month to form that month's beginning-of-month portfolio.
    """
    a = annual.copy()
    if a.empty:
        return pd.DataFrame(columns=["month"] + list(a.columns))
    a["effective"] = pd.PeriodIndex([pd.Period(f"{y}-12", freq="M") + lag_months for y in a["year"]], freq="M")
    if "available_date" in a:
        dates = pd.to_datetime(a["available_date"], errors="raise")
        actual = dates.dt.to_period("M") + 1
        a["effective"] = actual.where(dates.notna(), a["effective"])
    months = pd.PeriodIndex(months, freq="M").sort_values().unique()
    out = []
    for fid, g in a.groupby("firm_id"):
        g = g.sort_values("effective").set_index("effective")
        g = g[~g.index.duplicated(keep="last")]
        expanded = g.reindex(months, method="ffill")
        expanded["firm_id"] = fid
        expanded.index.name = "month"
        out.append(expanded.reset_index())
    res = pd.concat(out, ignore_index=True)
    return res.dropna(subset=["year"])
