import numpy as np
import pandas as pd

from esgx.measures.greenness import (
    greenness,
    greenness_table,
    scores_from_walk,
    tercile_labels,
)


def test_pst_formula_matches_lecture_example():
    # Lecture 4: (E_score 4.2, E_weight 48) -> -2.78 ; (4.1, 11) -> -0.65
    assert round(greenness(4.2, 48), 2) == -2.78
    assert round(greenness(4.1, 11), 2) == -0.65
    assert greenness(10.0, 48) == 0.0  # perfectly green firm


def _walk():
    firms = pd.DataFrame({"firm_id": list("ABCDEF"), "sector": ["Energy"] * 3 + ["Tech"] * 3})
    walk_scores = [2.0, 5.0, 8.0, 4.0, 6.0, 8.0]
    intensity = [90.0, 50.0, 20.0, 8.0, 5.0, 2.0]
    walk = pd.DataFrame({"firm_id": firms["firm_id"], "year": 2020, "sector": firms["sector"], "walk": walk_scores,
                         "intensity": intensity, "level": [i * 100.0 for i in intensity]})  # revenue 100 each
    return firms, walk


def test_walk_scores_give_dirtier_industry_larger_weight():
    _, walk = _walk()
    s = scores_from_walk(walk).set_index("firm_id")
    assert s.loc["A", "e_weight"] > s.loc["D", "e_weight"]
    assert (s["e_score"] == walk.set_index("firm_id")["walk"]).all()  # e_score IS the walk score
    assert s["e_score"].between(0, 10).all()


def test_greenness_decomposition_sums():
    firms, walk = _walk()
    g = greenness_table(scores_from_walk(walk), firms)
    assert np.allclose(g["g"], g["g_across"] + g["g_within"])
    # within-industry components average to zero per industry
    m = g.merge(firms, on="firm_id").groupby("sector")["g_within"].mean()
    assert np.allclose(m, 0.0)


def test_terciles():
    lab = tercile_labels(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert (lab == "green").sum() == 3 and (lab == "brown").sum() == 3
