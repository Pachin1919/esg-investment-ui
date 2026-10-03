"""Combined talk score: deterministic green-word intensity plus the LLM rubric in one number.

The two talk measures capture different things, which is why they are combined rather than
compared only (the side-by-side validation lives in ``greenwash.diagnostics`` and the
Deterministisk talk note):

* deterministic (``talk_dict``): the *volume* of green claims — claim-word hits per 1 000
  words, percentile-ranked within industry × year (Giannetti et al. 2023). Free, covers every
  firm with documents, but blind to content: a hedged aspiration counts like a quantified
  commitment, and word lists are gameable (Cao, Yang & Zhang: firms write for machine readers).
* LLM rubric (``talkwalk``): the *content* — ambition, specificity, forward-looking share,
  hedging, promotional tone, scored 0-10 on a fixed rubric with quoted evidence. Sees the
  difference word counts cannot, but costs per document, so coverage is sparse.

Combination (``combine_talk``):

1. z-score each measure within its own reference group: the dictionary score within
   industry × year (word-intensity baselines differ by industry), the LLM score within year
   across the universe (the rubric is absolute and coverage too sparse for industry cells;
   a group needs two scored firms for a z at all).
2. ``talk_combined_z`` = mean of the z's that exist; ``talk_source`` records which inputs
   contributed ("both", "dict", "llm", "none").
3. ``talk_combined`` = percentile of the combined z within industry × year, scaled 0-10 —
   the same scale and ranking convention as the other pillars, so it drops straight into the
   double-sort flag. The final within-industry ranking also re-anchors the universe-wide LLM
   z to industry peers.

``greenwashing_variants`` then flags greenwashers three ways side by side — dictionary talk
alone, LLM talk alone, and the combination — using the same cuts as ``greenwash`` (top
quintile talk, bottom tercile walk; Giannetti et al. 2023 × Liang, Sun & Teo 2022). A flag is
NaN, not 0, when its talk variant was not measured. Nothing here touches walk: text measures
never enter the walk pillar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.measures.greenwash import TALK_CUT, WALK_CUT
from esgx.measures.standardize import attach_sector, standardize_within
from esgx.measures.walk_hard import pct_score

VARIANTS = ("dict", "llm", "combined")


def combine_talk(
    talk_dict: pd.DataFrame,
    talk_llm: pd.DataFrame | None,
    firms: pd.DataFrame,
    industry_col: str = "sector",
    min_group: int = 5,
) -> pd.DataFrame:
    """Firm × year combined talk from the deterministic table (`talk_dict.talk_score` output)
    and the LLM table (`talkwalk.aggregate_firm_year` output; may be None or empty)."""
    det = talk_dict.rename(columns={"talk": "talk_dict"})
    keep = ["firm_id", "year", "talk_dict"] + [c for c in ("claim_per_1000", "risk_context_share") if c in det.columns]
    det = det[keep]
    if talk_llm is None or talk_llm.empty:
        llm = pd.DataFrame({"firm_id": pd.Series(dtype=det["firm_id"].dtype), "year": pd.Series(dtype=det["year"].dtype),
                            "talk_llm": pd.Series(dtype=float)})
    else:  # only the talk pillar: the LLM's walk sub-scores never enter anything here
        llm = talk_llm.rename(columns={"talk": "talk_llm"})[["firm_id", "year", "talk_llm"]]
    df = det.merge(llm, on=["firm_id", "year"], how="outer")
    df = attach_sector(df, firms, industry_col)
    size = df.groupby(["year", industry_col])["firm_id"].transform("count")
    df["rank_group"] = np.where(size >= min_group, df[industry_col].fillna("_all"), "_all")
    # z within each measure's own group: dict within industry × year, llm within year (sparse)
    df = standardize_within(df, ["talk_dict"], by=["year", "rank_group"], method="z")
    df = standardize_within(df, ["talk_llm"], by=["year"], method="z")
    zcols = ["talk_dict_z", "talk_llm_z"]
    df["talk_combined_z"] = df[zcols].mean(axis=1)
    df["n_sources"] = df[zcols].notna().sum(axis=1)
    has_d, has_l = df["talk_dict_z"].notna(), df["talk_llm_z"].notna()
    df["talk_source"] = np.select([has_d & has_l, has_d, has_l], ["both", "dict", "llm"], default="none")
    df["talk_combined"] = pct_score(df["talk_combined_z"], [df["year"], df["rank_group"]], lower_is_greener=False)
    cols = ["firm_id", "year", industry_col, "rank_group", "talk_dict", "talk_llm", "talk_dict_z", "talk_llm_z",
            "talk_combined_z", "talk_combined", "n_sources", "talk_source", "claim_per_1000", "risk_context_share"]
    return df[[c for c in cols if c in df.columns]].sort_values(["year", "firm_id"]).reset_index(drop=True)


def greenwashing_variants(combined: pd.DataFrame, walk: pd.DataFrame, industry_col: str = "sector") -> pd.DataFrame:
    """Combine the combined-talk table with the hard-data walk table: three talk variants,
    their gaps against walk, and the three greenwasher flags (NaN where a variant is unmeasured)."""
    wcols = ["firm_id", "year", industry_col, "intensity", "walk"]
    df = walk[[c for c in wcols if c in walk.columns]].merge(
        combined.drop(columns=[industry_col, "rank_group"], errors="ignore"), on=["firm_id", "year"], how="inner")
    for v in VARIANTS:
        t = f"talk_{v}"
        df[f"gap_{v}"] = df[t] - df["walk"]
        flag = ((df[t] >= TALK_CUT) & (df["walk"] <= WALK_CUT)).astype(float)
        df[f"greenwasher_{v}"] = flag.where(df[t].notna())  # NaN = variant not measured, not "clean"
    cols = ["firm_id", "year", industry_col, "greenwasher_dict", "greenwasher_llm", "greenwasher_combined",
            "talk_dict", "talk_llm", "talk_combined", "talk_source", "gap_dict", "gap_llm", "gap_combined",
            "walk", "intensity", "claim_per_1000", "risk_context_share"]
    return df[[c for c in cols if c in df.columns]].sort_values(
        ["year", "gap_combined"], ascending=[True, False]).reset_index(drop=True)
