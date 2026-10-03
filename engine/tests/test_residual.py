"""Excess talk on synthetic data: the residual removes what emissions explain and finds the over-talker."""

import numpy as np
import pandas as pd
import pytest

from esgx.measures.residual import LEVEL_ONLY, excess_talk


def _panel(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for year in (2022, 2023):
        for i in range(n):
            intensity = float(np.exp(rng.normal(6, 1.5)))
            claim = np.expm1(0.2 + 0.15 * np.log1p(intensity) + rng.normal(0, 0.05))  # dirtier firms write more
            rows.append({"firm_id": f"F{i}", "year": year, "sector": "Energy" if i % 2 else "Utilities",
                         "claim_per_1000": claim, "intensity": intensity, "d_log_intensity": rng.normal(0, 0.1), "n_words": 50_000})
    df = pd.DataFrame(rows)
    df.loc[(df["firm_id"] == "F7") & (df["year"] == 2023), "claim_per_1000"] *= 3  # same numbers, three times the claims
    return df


def test_residual_is_orthogonal_to_emissions_and_flags_the_over_talker():
    res, fit = excess_talk(_panel())
    assert fit.loc["log_intensity", "coef"] == pytest.approx(0.15, abs=0.03) and fit.loc["log_intensity", "t"] > 5
    assert abs(res["excess_talk"].corr(np.log1p(res["intensity"]))) < 0.05
    top = res.loc[res["excess_talk"].idxmax()]
    assert (top["firm_id"], top["year"]) == ("F7", 2023) and top["excess_talker"] == 1
    assert top["claim_per_1000"] > 2 * top["talk_expected"]
    assert res.groupby("year")["excess_talker"].mean().between(0.15, 0.25).all()


def test_level_only_spec_keeps_rows_without_a_trend_and_small_samples_raise():
    df = _panel()
    df.loc[df["year"] == 2022, "d_log_intensity"] = np.nan  # first year has no trend
    assert len(excess_talk(df)[0]) == 40 and len(excess_talk(df, regressors=LEVEL_ONLY)[0]) == 80
    with pytest.raises(ValueError):
        excess_talk(df.head(10))
