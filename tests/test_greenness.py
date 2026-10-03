import numpy as np
import pandas as pd

from esgx.measures.greenness import (
    greenness,
    greenness_table,
    scores_from_carbon_intensity,
    tercile_labels,
)


def test_pst_formula_matches_lecture_example():
    # Lecture 4: Exxon (E_score 4.2, E_weight 48) -> -2.78 ; Best Buy (4.1, 11) -> -0.65
    assert round(greenness(4.2, 48), 2) == -2.78
    assert round(greenness(4.1, 11), 2) == -0.65
    assert greenness(10.0, 48) == 0.0  # perfectly green firm


def _toy():
    firms = pd.DataFrame(
        {"firm_id": list("ABCDEF"), "sector": ["Energy"] * 3 + ["Tech"] * 3}
    )
    inten = pd.DataFrame(
        {
            "firm_id": list("ABCDEF"),
            "year": [2020] * 6,
            "intensity": [900.0, 300.0, 100.0, 5.0, np.nan, 1.0],
            "matched": [True, True, True, True, False, True],
        }
    )
    return firms, inten


def test_proxy_scores_rank_within_and_across_industry():
    firms, inten = _toy()
    s = scores_from_carbon_intensity(inten, firms)
    s = s.set_index("firm_id")
    # dirtier industry gets larger E_weight
    assert s.loc["A", "e_weight"] > s.loc["D", "e_weight"]
    # within Energy, A (dirtiest) has lowest e_score
    assert s.loc["A", "e_score"] < s.loc["B", "e_score"] < s.loc["C", "e_score"]
    # unmatched E treated as clean (score at least as high as any matched peer)
    assert s.loc["E", "e_score"] >= s.loc["D", "e_score"]
    assert s["e_score"].between(0, 10).all()


def test_greenness_decomposition_sums():
    firms, inten = _toy()
    g = greenness_table(scores_from_carbon_intensity(inten, firms), firms)
    assert np.allclose(g["g"], g["g_across"] + g["g_within"])
    # within-industry components average to zero per industry
    m = g.merge(firms, on="firm_id").groupby("sector")["g_within"].mean()
    assert np.allclose(m, 0.0)


def test_terciles():
    lab = tercile_labels(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert (lab == "green").sum() == 3 and (lab == "brown").sum() == 3
