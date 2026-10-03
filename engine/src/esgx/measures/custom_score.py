"""Our own greenness score: a weighted combination of pillars, exposed in the same
(e_score, e_weight) shape as commercial providers so every downstream module
(greenness_table, GMB, Fama-MacBeth) works unchanged.

Pillars are firm × year columns in [0, 10] (10 = greenest). Typical pillars:
  * carbon      – within-industry rank of scope-1 intensity (from scores_from_carbon_intensity)
  * walk        – LLM-scored actions (targets met, capex, verified data, emissions trend)
  * talk        – LLM-scored ambition of language (NOT a green pillar by itself)
  * gap         – talk − walk, high = greenwashing risk  (enters with a NEGATIVE weight)

The E_weight pillar (industry materiality) is kept from the carbon proxy or a provider.

Weights are a plain dict so they can be tuned or swept in a backtest:
    ScoreSpec(weights={"carbon": 0.5, "walk": 0.4, "gap": -0.1})
Missing pillars are ignored and the remaining weights renormalised per firm-year.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from esgx.schema import validate

DEFAULT_WEIGHTS = {"carbon": 0.5, "walk": 0.4, "gap": -0.1}


@dataclass
class ScoreSpec:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    provider: str = "esgx_custom"

    def validate(self) -> None:
        pos = sum(w for w in self.weights.values() if w > 0)
        if pos <= 0:
            raise ValueError("at least one pillar must have a positive weight")


def combine_pillars(pillars: pd.DataFrame, e_weight: pd.DataFrame, spec: ScoreSpec | None = None) -> pd.DataFrame:
    """pillars: firm_id, year, <pillar columns in 0..10>.  e_weight: firm_id, year, e_weight.
    Returns an `esg_scores` table with provider = spec.provider."""
    spec = spec or ScoreSpec()
    spec.validate()
    cols = [c for c in spec.weights if c in pillars.columns]
    if not cols:
        raise ValueError(f"none of the pillars {list(spec.weights)} found in {list(pillars.columns)}")
    df = pillars[["firm_id", "year"] + cols].copy()

    # negative-weight pillars are "bad" scores: flip so 10 is always the green end
    for c in cols:
        if spec.weights[c] < 0:
            df[c] = 10.0 - df[c]
    w = pd.Series({c: abs(spec.weights[c]) for c in cols})
    vals = df[cols].to_numpy(dtype=float)
    mask = ~np.isnan(vals)
    weights = np.where(mask, w.to_numpy()[None, :], 0.0)
    denom = weights.sum(axis=1)
    score = np.where(denom > 0, np.nansum(vals * weights, axis=1) / np.where(denom > 0, denom, 1), np.nan)
    df["e_score"] = np.clip(score, 0, 10)
    df["provider"] = spec.provider
    out = df.merge(e_weight[["firm_id", "year", "e_weight"]], on=["firm_id", "year"], how="left")
    return validate(out[["firm_id", "year", "provider", "e_score", "e_weight"]], "esg_scores")


def pillar_from_rank(series: pd.Series, groups: pd.Series | None = None, higher_is_greener: bool = True) -> pd.Series:
    """Map any numeric firm-level variable to a 0..10 pillar by (within-group) percentile rank."""
    if groups is None:
        r = series.rank(pct=True, method="average")
    else:
        r = series.groupby(groups).rank(pct=True, method="average")
    return (10.0 * r) if higher_is_greener else (10.0 * (1.0 - r) + 10.0 / (2 * series.groupby(groups).transform("size") if groups is not None else 2 * len(series)))
