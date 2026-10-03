import numpy as np
import pandas as pd

from esgx.measures.custom_score import ScoreSpec, combine_pillars


def test_combine_pillars_weights_and_gap_flip():
    pillars = pd.DataFrame(
        {"firm_id": ["A", "B", "C"], "year": [2023] * 3,
         "carbon": [10.0, 2.0, 6.0], "walk": [8.0, 2.0, np.nan], "gap": [0.0, 10.0, 5.0]}
    )
    ew = pd.DataFrame({"firm_id": ["A", "B", "C"], "year": [2023] * 3, "e_weight": [30.0, 30.0, 30.0]})
    out = combine_pillars(pillars, ew, ScoreSpec(weights={"carbon": 0.5, "walk": 0.4, "gap": -0.1})).set_index("firm_id")
    # A: 0.5*10 + 0.4*8 + 0.1*(10-0) = 5+3.2+1 = 9.2
    assert abs(out.loc["A", "e_score"] - 9.2) < 1e-9
    # B: 0.5*2 + 0.4*2 + 0.1*(10-10) = 1.8
    assert abs(out.loc["B", "e_score"] - 1.8) < 1e-9
    # C: walk missing -> renormalise over carbon (0.5) and gap (0.1): (0.5*6 + 0.1*5)/0.6
    assert abs(out.loc["C", "e_score"] - (3.0 + 0.5) / 0.6) < 1e-9
    assert (out["provider"] == "esgx_custom").all()
    assert out["e_score"].between(0, 10).all()
