import numpy as np
import pandas as pd

from esgx.measures.carbon import carbon_intensity
from esgx.measures.greenwash import diagnostics, greenwashing_table
from esgx.measures.talk_dict import count_text, firm_year_intensity, talk_score
from esgx.measures.walk_hard import pct_score, walk_score

FIRMS = pd.DataFrame({"firm_id": [f"F{i}" for i in range(6)], "sector": ["Energy"] * 6})


def _carbon():
    # F0 cleanest and falling, F5 dirtiest and rising; equal revenue so intensity ~ scope 1
    rows, fund = [], []
    for i in range(6):
        for y, growth in ((2022, 1.0), (2023, 0.8 + 0.08 * i)):
            rows.append({"firm_id": f"F{i}", "year": y, "scope1": 100.0 * (i + 1) * growth, "scope2": np.nan, "scope3": np.nan, "source": "syn", "matched": True})
            fund.append({"firm_id": f"F{i}", "year": y, "revenue": 1000.0, "book_equity": 1.0})
    return carbon_intensity(pd.DataFrame(rows), pd.DataFrame(fund))


def test_pct_score_bounds_and_single_member_group():
    x = pd.Series([1.0, 2.0, 3.0, 9.0])
    g = pd.Series(["a", "a", "a", "b"])
    s = pct_score(x, [g])
    assert s.iloc[0] == 10 and s.iloc[2] == 0 and s.iloc[3] == 5


def test_walk_orders_firms_by_hard_data():
    w = walk_score(_carbon(), FIRMS)
    y23 = w[w["year"] == 2023].set_index("firm_id")
    assert y23.loc["F0", "walk"] == 10 and y23.loc["F5", "walk"] == 0 and y23["walk"].is_monotonic_decreasing
    # walk is the level component alone; trends are separate columns
    assert (y23["walk"] == y23["walk_intensity_level"]).all() and y23["walk_intensity_trend"].notna().all()
    # first year has no trend: score comes from the level component alone
    assert (w.loc[w["year"] == 2022, "walk_n_components"] == 1).all()


def test_talk_is_word_intensity_not_length():
    green = "We reduce carbon emissions and invest in renewable energy. "
    plain = "We sell products to customers in many regions every quarter. "
    assert count_text(green)["n_claim"] > 0 and count_text(plain)["n_claim"] == 0
    counts = pd.DataFrame([{"firm_id": f"F{i}", "year": 2023, "accession": f"a{i}", **count_text(green * (i + 1) + plain * 20 * (6 - i))} for i in range(6)])
    t = talk_score(firm_year_intensity(counts), FIRMS).set_index("firm_id")
    assert t["talk"].is_monotonic_increasing and t.loc["F5", "talk"] == 10
    # doubling the report without changing the mix leaves the intensity unchanged
    a, b = count_text(green + plain), count_text((green + plain) * 2)
    assert abs(a["n_claim"] / a["n_words"] - b["n_claim"] / b["n_words"]) < 1e-9


def test_risk_context_and_commodity_words_are_not_claims():
    claim = "Our net zero plan cuts carbon emissions through renewable power purchases across all plants."
    risk = "Climate regulation and carbon costs are a risk that may adversely impact our results."
    product = "We produce oil and natural gas and sell coal to utilities in several regions."
    assert count_text(claim)["n_claim"] >= 3
    r = count_text(risk)
    assert r["n_claim_all"] >= 2 and r["n_claim"] == 0
    p = count_text(product)
    assert p["n_green"] >= 3 and p["n_claim_all"] == 0


def test_gap_flags_loud_dirty_firm():
    w = walk_score(_carbon(), FIRMS)
    green = "carbon emissions renewable climate "
    counts = pd.DataFrame([{"firm_id": f"F{i}", "year": 2023, "accession": f"a{i}", **count_text(green * (i + 1) + "ordinary business text here " * 50)} for i in range(6)])
    gw = greenwashing_table(talk_score(firm_year_intensity(counts), FIRMS), w).set_index("firm_id")
    assert gw.loc["F5", "gap"] == 10 and gw.loc["F5", "greenwasher"] == 1
    assert gw.loc["F0", "gap"] == -10 and gw.loc["F0", "greenhusher"] == 1
    assert gw["gap"].between(-10, 10).all()
    assert gw.iloc[0]["greenwasher"] == 1  # flagged firms sort first
    d = diagnostics(gw)
    assert d.loc[2023, "corr_talk_walk"] < -0.9 and d.loc[2023, "greenwashers"] >= 1
