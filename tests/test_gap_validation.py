import numpy as np
import pandas as pd
import pytest

from esgx.measures.gap import GAP_COLUMNS, gap_variants
from esgx.measures.standardize import standardize_within
from esgx.measures.validation import emissions_outcomes, predictive_regression

rng = np.random.default_rng(0)


def _panel(n_firms=40, years=(2021, 2022, 2023)):
    firms = pd.DataFrame({"firm_id": [f"F{i}" for i in range(n_firms)], "sector": ["Energy" if i % 2 else "Tech" for i in range(n_firms)]})
    rows = []
    for f in firms.itertuples():
        base_walk = rng.uniform(2, 8)
        for y in years:
            walk = base_walk + rng.normal(0, 0.5)
            talk = 0.5 * walk + rng.normal(0, 1.5) + (3 if f.firm_id in ("F0", "F2") else 0)
            rows.append({"firm_id": f.firm_id, "year": y, "talk": np.clip(talk, 0, 10), "walk": np.clip(walk, 0, 10)})
    return pd.DataFrame(rows), firms


def test_standardize_z_and_pct_within_groups():
    fy, firms = _panel()
    df = standardize_within(fy.merge(firms, on="firm_id"), ["talk"], by=["year", "sector"], method="z")
    stats = df.groupby(["year", "sector"])["talk_z"].agg(["mean", "std"])
    assert np.allclose(stats["mean"], 0, atol=1e-9) and np.allclose(stats["std"], 1, atol=1e-9)
    df = standardize_within(fy.merge(firms, on="firm_id"), ["talk"], by=["year"], method="pct")
    assert df["talk_pct"].between(0, 1).all()


def test_gap_variants_flag_loud_low_walk_firms():
    fy, firms = _panel()
    out = gap_variants(fy, firms)
    assert all(c in out for c in GAP_COLUMNS)
    # F0 and F2 got +3 talk on top of their walk: highest residual gap on average
    top = out.groupby("firm_id")["gap_resid"].mean().sort_values(ascending=False).index[:2]
    assert set(top) == {"F0", "F2"}
    # the flag requires both high talk and low walk, so it is rarer than high talk alone
    assert 0 < out["greenwasher"].sum() < (out["talk_rank"] >= 0.8).sum()


def test_predictive_regression_recovers_walk_not_talk():
    fy, firms = _panel(n_firms=80, years=(2020, 2021, 2022, 2023))
    # next-year emissions fall with walk, are unrelated to talk
    em_rows = []
    for f, g in fy.groupby("firm_id"):
        level = 1000.0
        for r in g.sort_values("year").itertuples():
            em_rows.append({"firm_id": f, "year": r.year, "scope1": level, "scope2": np.nan, "scope3": np.nan, "source": "syn", "matched": True})
            level *= np.exp(-0.05 * r.walk + rng.normal(0, 0.05))
    emissions = pd.DataFrame(em_rows)
    fundamentals = emissions[["firm_id", "year"]].assign(revenue=100.0, book_equity=50.0)
    tab = predictive_regression(fy.merge(firms, on="firm_id"), emissions_outcomes(emissions, fundamentals))
    assert tab.loc["walk", "coef"] < 0 and tab.loc["walk", "t"] < -3
    assert abs(tab.loc["talk", "t"]) < 2


def test_predictive_regression_needs_enough_rows():
    fy, firms = _panel(n_firms=5, years=(2022,))
    oc = pd.DataFrame({"firm_id": fy["firm_id"], "year": fy["year"], "d_log_scope1_next": 0.0, "log_revenue": 1.0})
    with pytest.raises(ValueError):
        predictive_regression(fy.merge(firms, on="firm_id"), oc)
