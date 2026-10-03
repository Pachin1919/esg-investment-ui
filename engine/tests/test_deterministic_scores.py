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


def test_document_metrics_roundtrip_and_recount(tmp_path, monkeypatch):
    import json

    from esgx.measures import text_metrics as tx
    from esgx.measures.talk_dict import counts_from_terms

    monkeypatch.setattr(tx, "METRICS_DIR", tmp_path)
    text = ("Our net zero plan cuts carbon emissions with renewable power. " * 5 + "Soil quality and window frames are unrelated. "
            + "Climate regulation is a risk that may impact costs. " + "We sell oil and gas. " * 3)
    m = tx.document_metrics(text)
    assert "oil" in m["terms"] and "soil" not in "".join(m["terms"])  # word-start match: "soil" and "window" are not hits
    assert m["terms"]["climate"] == [1, 0]  # the only climate hit sits in risk context
    assert m["counts"]["n_green"] > m["counts"]["n_claim_all"] > m["counts"]["n_claim"] > 0
    p = tx.write_metrics("hk", {"firm_id": "0001.HK", "year": 2024, "form": "esg_report", "filing_date": "2025-04-01", "accession": "doc1"}, m)
    assert tx.is_current(p) and json.loads(p.read_text())["sentiment"]["n_env_hits"] > 0
    flat = tx.load_metrics("hk")
    assert flat.loc[0, "n_claim"] == m["counts"]["n_claim"] and "glossiness" in flat and "claim_per_1000" in flat
    # the stored per-term counts are enough to recompute talk under a different claim dictionary
    narrow = counts_from_terms(m["counts"]["n_words"], m["terms"], claim_terms=["net zero", "renewable"])
    # 5 "net zero" + 5 "renewable"; the last "renewable" falls inside the risk window of the next sentence
    assert narrow["n_claim_all"] == 10 and narrow["n_claim"] == 9 and narrow["n_green"] == m["counts"]["n_green"]


def test_greenness_uses_walk_as_e_score():
    from esgx.measures.greenness import greenness_table, scores_from_walk

    firms = pd.DataFrame({"firm_id": [f"C{i}" for i in range(5)] + [f"S{i}" for i in range(5)], "sector": ["Cement"] * 5 + ["Software"] * 5})
    em = pd.DataFrame({"firm_id": firms["firm_id"], "year": 2025, "scope1": [5000, 4000, 3000, 2000, 1000, 5, 4, 3, 2, 1],
                       "scope2": np.nan, "scope3": np.nan, "source": "syn", "matched": True})
    fund = pd.DataFrame({"firm_id": firms["firm_id"], "year": 2025, "revenue": 100.0, "book_equity": 1.0})
    walk = walk_score(carbon_intensity(em, fund), firms)
    scores = scores_from_walk(walk)
    m = scores.merge(walk[["firm_id", "walk"]], on="firm_id")
    assert (m["e_score"] == m["walk"]).all()  # one objective number, shared by both measures
    g = greenness_table(scores, firms).set_index("firm_id")
    # same walk rank, but the cement firm is browner because its industry weighs more
    assert g.loc["C0", "e_score"] == g.loc["S0", "e_score"] == 0 and g.loc["C0", "g"] < g.loc["S0", "g"] < 0
    assert g.loc["C4", "g"] == 0 and g.loc["S4", "g"] == 0  # cleanest in its industry: g = 0
    assert g["e_weight"].between(5, 50).all() and g.loc["C0", "e_weight"] > g.loc["S0", "e_weight"]
    assert abs(g.loc["C0", "g"] + (10 - 0) * g.loc["C0", "e_weight"] / 100) < 1e-9


def test_walk_pillars_add_water_waste_energy_next_to_carbon():
    from esgx.measures.walk_pillars import walk_pillars

    firms = pd.DataFrame({"firm_id": [f"F{i}" for i in range(6)], "sector": ["Chips"] * 6})
    em = pd.DataFrame({"firm_id": firms["firm_id"], "year": 2025, "scope1": [10.0, 20, 30, 40, 50, 60], "scope2": np.nan, "scope3": [5.0, np.nan, 0, 1, 1, 1],
                       "source": "syn", "matched": True,
                       "water_tonnes": [600.0, 500, 400, 300, 200, np.nan],       # the cleanest carbon firm uses most water
                       "waste_tonnes": [1.0, 2, 3, 4, 5, 6], "renewable_share_pct": [50.0, np.nan, np.nan, np.nan, np.nan, 0.0]})
    fund = pd.DataFrame({"firm_id": firms["firm_id"], "year": 2025, "revenue": 100.0, "book_equity": 1.0})
    carbon = carbon_intensity(em, fund)
    out = walk_pillars(walk_score(carbon, firms), em, carbon).set_index("firm_id")
    assert (out["pillar_carbon"] == out["walk"]).all()
    assert out.loc["F0", "pillar_water"] == 0 and out.loc["F4", "pillar_water"] == 10 and pd.isna(out.loc["F5", "pillar_water"])
    assert out.loc["F0", "pillar_energy"] == 10 and out.loc["F5", "pillar_energy"] == 0
    # F0: carbon 10, water 0, waste 10, energy 10 -> 7.5; missing pillars are skipped, not penalised
    assert out.loc["F0", "walk_multi"] == 7.5 and out.loc["F0", "walk_n_pillars"] == 4
    assert out.loc["F1", "walk_n_pillars"] == 3 and out.loc["F5", "walk_n_pillars"] == 3
    assert bool(out.loc["F0", "scope3_reported"]) and not out.loc["F1", "scope3_reported"] and not out.loc["F2", "scope3_reported"]
    heavy_carbon = walk_pillars(walk_score(carbon, firms), em, carbon, weights={"carbon": 3.0, "water": 1.0}).set_index("firm_id")
    assert heavy_carbon.loc["F0", "walk_multi"] == 7.5 and abs(heavy_carbon.loc["F4", "walk_multi"] - (3 * 2 + 10) / 4) < 1e-9
