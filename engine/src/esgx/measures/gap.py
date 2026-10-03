"""Greenwashing gap, three ways. The literature never uses a raw talk − walk difference; it
always measures talk *given* walk on comparable scales:

1. ``gap_z``     : z(talk) − z(walk), both standardised within industry × year.
2. ``gap_resid`` : residual of talk regressed on walk within industry × year (talk the walk
                   level does not explain). Robust to legitimate talk–walk correlation.
3. ``greenwasher``: 1 if talk is in the top quintile and walk in the bottom tercile of the year
                   (Liang, Sun & Teo 2022 define greenwashers as signatories in the bottom
                   tercile of holdings-based ESG; Giannetti et al. 2023 use top-quintile talkers).

Input is the firm × year table from `talkwalk.aggregate_firm_year` plus `firms` for the industry.
All three are reported side by side; none replaces the 0–10 pillars (talk and walk stay separate).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.measures.standardize import attach_sector, standardize_within


def _resid_within(df: pd.DataFrame, y: str, x: str, by: list[str]) -> pd.Series:
    """OLS residual of y on x (with intercept) estimated separately in each group."""
    out = pd.Series(np.nan, index=df.index)
    for _, g in df.dropna(subset=[y, x]).groupby(by, dropna=False):
        if len(g) < 3 or g[x].std() == 0:
            continue
        b = np.cov(g[x], g[y], ddof=0)[0, 1] / g[x].var(ddof=0)
        a = g[y].mean() - b * g[x].mean()
        out.loc[g.index] = g[y] - (a + b * g[x])
    return out


def gap_variants(
    firm_year: pd.DataFrame,
    firms: pd.DataFrame,
    industry_col: str = "sector",
    talk_q: float = 0.8,
    walk_q: float = 1 / 3,
) -> pd.DataFrame:
    """Return firm_year with gap_raw, gap_z, gap_resid, talk_rank, walk_rank and greenwasher.

    ``talk_q`` / ``walk_q`` are the percentile cut-offs for the flag (top quintile talk, bottom
    tercile walk by default), computed within year across the whole universe so that the flag
    is comparable with the hedge-fund and bank definitions, which are not industry-adjusted.
    """
    df = attach_sector(firm_year, firms, industry_col)
    by = ["year", industry_col]
    df = standardize_within(df, ["talk", "walk"], by=by, method="z")
    df["gap_raw"] = df["talk"] - df["walk"]
    df["gap_z"] = df["talk_z"] - df["walk_z"]
    df["gap_resid"] = _resid_within(df, "talk", "walk", by)
    yr = df.groupby("year")
    df["talk_rank"] = yr["talk"].rank(pct=True, method="average")
    df["walk_rank"] = yr["walk"].rank(pct=True, method="average")
    df["greenwasher"] = ((df["talk_rank"] >= talk_q) & (df["walk_rank"] <= walk_q)).astype(int)
    return df


GAP_COLUMNS = ["gap_raw", "gap_z", "gap_resid", "greenwasher"]
