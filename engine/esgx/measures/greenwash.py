"""Greenwashing from the deterministic talk and walk scores.

Primary measure: the double sort used in the literature. A firm-year is flagged ``greenwasher``
when talk is in the top quintile (Giannetti et al. 2023, "high environmental reporter") and walk
in the bottom tercile (Liang, Sun & Teo 2022) of its industry and year. ``greenhusher`` is the
mirror image (Chen 2025: doing without saying).

Secondary measure: gap = talk − walk in [−10, 10]. Both are 0-10 percentiles within the same
industry and year, so the difference is between like quantities, but no paper differences the
two: a gap fixes the weights at +1 / −1 and cannot tell quiet-and-dirty from loud-and-average.
Talk and walk are always reported next to it.

`diagnostics` checks the main threat to the measure: if talk is strongly negatively related to
walk within industry, dirty firms simply write more about emissions and the gap only re-measures
brownness.
"""

from __future__ import annotations

import pandas as pd

TALK_CUT = 8.0  # top quintile of a 0-10 percentile score
WALK_CUT = 10.0 / 3.0  # bottom tercile


def greenwashing_table(talk: pd.DataFrame, walk: pd.DataFrame) -> pd.DataFrame:
    """Inner join of the two firm × year tables: flags, talk, walk, gap and the inputs behind them."""
    t = talk[["firm_id", "year", "n_docs", "n_words", "n_claim", "claim_per_1000", "risk_context_share", "talk", "talk_unfiltered"]]
    w = walk[["firm_id", "year", "sector", "intensity", "walk", "walk_intensity_trend", "walk_emission_trend", "walk_composite"]]
    df = w.merge(t, on=["firm_id", "year"], how="inner")
    df["greenwasher"] = ((df["talk"] >= TALK_CUT) & (df["walk"] <= WALK_CUT)).astype(int)
    df["greenhusher"] = ((df["talk"] <= 10.0 - TALK_CUT) & (df["walk"] >= 10.0 - WALK_CUT)).astype(int)
    df["gap"] = df["talk"] - df["walk"]
    cols = ["firm_id", "year", "sector", "greenwasher", "greenhusher", "talk", "walk", "gap", "talk_unfiltered", "claim_per_1000",
            "risk_context_share", "n_claim", "n_words", "n_docs", "intensity", "walk_intensity_trend", "walk_emission_trend", "walk_composite"]
    return df[cols].sort_values(["year", "greenwasher", "gap"], ascending=[True, False, False]).reset_index(drop=True)


def diagnostics(gw: pd.DataFrame) -> pd.DataFrame:
    """Per year: firms, Spearman correlation of walk with talk (filtered and unfiltered), flag counts.
    A talk–walk correlation near −1 means the text measure mostly re-measures emissions."""
    rows = []
    for year, g in gw.groupby("year"):
        rows.append({"year": year, "n": len(g),
                     "corr_talk_walk": g["talk"].corr(g["walk"], method="spearman"),
                     "corr_unfiltered_walk": g["talk_unfiltered"].corr(g["walk"], method="spearman"),
                     "greenwashers": int(g["greenwasher"].sum()), "greenhushers": int(g["greenhusher"].sum())})
    return pd.DataFrame(rows).set_index("year")
