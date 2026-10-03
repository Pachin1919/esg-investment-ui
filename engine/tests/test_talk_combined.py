import numpy as np
import pandas as pd

from esgx.measures.talk_combined import combine_talk, greenwashing_variants

FIRMS = pd.DataFrame({"firm_id": [f"F{i}" for i in range(6)], "sector": ["Energy"] * 6})
YEAR = 2024


def _dict_talk(vals=(0.0, 2.0, 4.0, 6.0, 8.0, 10.0)):
    return pd.DataFrame({"firm_id": FIRMS["firm_id"], "year": YEAR, "talk": list(vals), "claim_per_1000": list(vals)})


def _llm_talk(mapping, **extra_cols):
    df = pd.DataFrame({"firm_id": list(mapping), "year": YEAR, "talk": list(mapping.values())})
    for k, v in extra_cols.items():
        df[k] = v
    return df


def _walk():
    return pd.DataFrame({"firm_id": FIRMS["firm_id"], "year": YEAR, "sector": "Energy",
                         "intensity": [10.0, 20, 30, 40, 50, 60], "walk": [10.0, 8, 6, 4, 2, 0]})


def test_no_llm_falls_back_to_dict_unchanged():
    for empty in (None, pd.DataFrame(columns=["firm_id", "year", "talk"])):
        c = combine_talk(_dict_talk(), empty, FIRMS).set_index("firm_id")
        assert (c["talk_source"] == "dict").all() and (c["n_sources"] == 1).all()
        # z-scoring is monotonic within the group, so the combined percentile reproduces the dict score
        assert (c["talk_combined"] == c["talk_dict"]).all() and c["talk_llm"].isna().all()


def test_combined_z_is_mean_of_available_z_scores():
    llm = _llm_talk({"F2": 9.0, "F3": 3.0, "F4": 7.0, "F5": 5.0}, walk=[1.0] * 4, gap=[2.0] * 4)  # extra cols ignored
    c = combine_talk(_dict_talk(), llm, FIRMS).set_index("firm_id")
    assert "walk" not in c.columns and "gap" not in c.columns  # the LLM walk pillar never leaks in
    z_d = (c["talk_dict"] - 5.0) / np.std([0, 2, 4, 6, 8, 10], ddof=1)
    z_l = (c["talk_llm"] - 6.0) / np.std([9, 3, 7, 5], ddof=1)  # llm z is across the whole year (sparse coverage)
    assert (c.loc[["F0", "F1"], "talk_source"] == "dict").all() and (c.loc[["F2", "F3", "F4", "F5"], "talk_source"] == "both").all()
    assert np.allclose(c.loc[["F0", "F1"], "talk_combined_z"], z_d.loc[["F0", "F1"]])
    assert np.allclose(c.loc[["F2", "F3", "F4", "F5"], "talk_combined_z"], (z_d + z_l).loc[["F2", "F3", "F4", "F5"]] / 2)
    assert c["talk_combined"].between(0, 10).all() and c["talk_combined"].idxmax() == "F4"  # strong on both measures beats loud on one


def test_single_llm_firm_in_a_year_gets_no_z():
    c = combine_talk(_dict_talk(), _llm_talk({"F3": 9.0}), FIRMS).set_index("firm_id")
    assert pd.isna(c.loc["F3", "talk_llm_z"]) and c.loc["F3", "talk_source"] == "dict"  # a z needs two firms in the group


def test_flags_follow_each_variant_and_nan_means_not_measured():
    # the LLM disagrees with the dictionary: F5 shouts in word counts but the rubric reads it as quiet; F4 is the glossy one
    llm = _llm_talk({"F4": 10.0, "F5": 0.0, "F3": 5.0})
    c = combine_talk(_dict_talk((0.0, 1.0, 3.0, 5.0, 7.0, 10.0)), llm, FIRMS)  # F4 dict = 7: under the top-quintile cut
    gw = greenwashing_variants(c, _walk()).set_index("firm_id")
    assert gw.loc["F5", "greenwasher_dict"] == 1 and gw.loc["F4", "greenwasher_dict"] == 0  # dict: F5 loudest (10) and dirtiest (0)
    assert gw.loc["F4", "greenwasher_llm"] == 1 and gw.loc["F5", "greenwasher_llm"] == 0    # llm: F4 glossy (10) and brown (2)
    assert gw["greenwasher_llm"].isna().sum() == 3  # F0-F2 have no llm score: NaN, not 0
    assert gw.loc["F5", "gap_dict"] == 10 and gw.loc["F0", "gap_dict"] == -10
    assert gw.loc["F4", "gap_llm"] == 8 and pd.isna(gw.loc["F0", "gap_llm"])
    # combined sits between its inputs for F4: z(10 of 0..10) and z(10 of [5,10,0]) averaged, still above the cut
    assert gw.loc["F4", "greenwasher_combined"] == 1 and gw.loc["F4", "talk_source"] == "both"
