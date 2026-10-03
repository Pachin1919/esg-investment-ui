"""Multi-pillar walk: the other reported environmental figures next to carbon.

`walk` (carbon intensity ranked within industry) stays the anchor, because that is the measure the
return literature prices (Bolton & Kacperczyk 2021; Crosignani et al. 2025; Pástor, Stambaugh &
Taylor 2022). Commercial E scores, which PST use, aggregate more environmental categories than
carbon; the same categories are mandatory KPIs in the disclosure regimes of our markets (HKEX ESG
Guide A1-A2, TWSE ESG platform). Each becomes a 0-10 pillar by percentile rank within the same
industry-year groups as walk (10 = greenest):

  carbon : (scope 1 + 2) / revenue          lower is greener   = walk
  water  : water consumption / revenue      lower is greener
  waste  : total waste / revenue            lower is greener
  energy : renewable share of total energy  higher is greener

`walk_multi` is the weighted mean of the pillars a firm reports (weights renormalised over the
available ones). No paper gives the weights: the default is equal weights, in the spirit of
Gibson Brandon et al. (2022), who average standardised scores across sources without weighting.
Pass other weights to test sensitivity.

Not ranked, kept as flags:
* scope 3 - coverage of categories differs so much between firms that a level ranking would
  punish the firms that report most; `scope3_reported` records disclosure only.
* verification - `verified` is carried along; rank verified firms separately as a robustness check.

Limit: a pillar a firm does not report is skipped, not penalised, so silence is not punished.
`walk_n_pillars` says how many pillars are behind each score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from esgx.measures.walk_hard import pct_score

# pillar -> (numerator column in the emissions table, divide by revenue?, lower is greener?)
PILLARS = {
    "water": ("water_tonnes", True, True),
    "waste": ("waste_tonnes", True, True),
    "energy": ("renewable_share_pct", False, False),
}
PILLAR_WEIGHTS = {"carbon": 1.0, "water": 1.0, "waste": 1.0, "energy": 1.0}


def walk_pillars(walk: pd.DataFrame, emissions: pd.DataFrame, carbon: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Add pillar scores, `walk_multi`, `walk_n_pillars` and `scope3_reported` to the walk table.
    `walk` from `walk_hard.walk_score`, `carbon` from `carbon.carbon_intensity` (for revenue),
    `emissions` with any of the PILLARS source columns (missing columns give empty pillars)."""
    w = weights or PILLAR_WEIGHTS
    src = [c for c, _, _ in PILLARS.values() if c in emissions.columns]
    extra = emissions[["firm_id", "year", *src] + (["scope3"] if "scope3" in emissions.columns else [])]
    df = walk.merge(extra, on=["firm_id", "year"], how="left").merge(carbon[["firm_id", "year", "revenue"]], on=["firm_id", "year"], how="left")
    groups = [df["year"], df["rank_group"]]
    df["pillar_carbon"] = df["walk"]
    for name, (col, per_revenue, lower) in PILLARS.items():
        if col not in df.columns:
            df[f"pillar_{name}"] = np.nan
            continue
        x = df[col] / df["revenue"].where(df["revenue"] > 0) if per_revenue else df[col]
        df[f"{name}_metric"] = x
        df[f"pillar_{name}"] = pct_score(x, groups, lower_is_greener=lower)
    cols = [f"pillar_{p}" for p in w]
    vals = df[cols].to_numpy(dtype=float)
    wts = np.where(~np.isnan(vals), np.array(list(w.values()))[None, :], 0.0)
    denom = wts.sum(axis=1)
    df["walk_multi"] = np.where(denom > 0, np.nansum(vals * wts, axis=1) / np.where(denom > 0, denom, 1), np.nan)
    df["walk_n_pillars"] = (~np.isnan(vals)).sum(axis=1)
    df["scope3_reported"] = df["scope3"].notna() & (df["scope3"] > 0) if "scope3" in df.columns else False
    return df.drop(columns=["revenue"])
