import numpy as np
import pandas as pd

from esgx.factors.famamacbeth import fama_macbeth
from esgx.factors.gmb import gmb_regression, gmb_sorted


def _panel(seed=0, n=120, T=48, slope=0.01):
    rng = np.random.default_rng(seed)
    months = pd.period_range("2015-01", periods=T, freq="M")
    g = rng.normal(-1.0, 0.8, n)
    rows = []
    for m in months:
        f = rng.normal(0, 0.02)  # market
        for i in range(n):
            rows.append({"firm_id": f"F{i}", "month": m, "g": g[i], "mktcap": 1e9 * (1 + i / n),
                         "ret": 0.005 + f + slope * g[i] + rng.normal(0, 0.03)})
    panel = pd.DataFrame(rows)
    factors = pd.DataFrame({"month": months, "mkt_rf": rng.normal(0, 0.02, T), "rf": 0.0})
    return panel, factors


def test_gmb_sorted_positive_when_green_earns_more():
    panel, _ = _panel(slope=0.02)
    s = gmb_sorted(panel)
    assert len(s) == 48
    assert s["gmb"].mean() > 0


def test_gmb_regression_recovers_slope_sign():
    panel, factors = _panel(slope=0.02, T=60)
    r = gmb_regression(panel, factors, window=24)
    assert r["gmb_reg"].dropna().mean() > 0


def test_fama_macbeth_recovers_coefficient():
    rng = np.random.default_rng(1)
    rows = []
    for y in range(2010, 2022):
        x = rng.normal(size=200)
        rows += [{"year": y, "x": xi, "y": 0.5 * xi + rng.normal(scale=0.5)} for xi in x]
    tab = fama_macbeth(pd.DataFrame(rows), y="y", xs=["x"])
    assert abs(tab.loc["x", "coef"] - 0.5) < 0.1
    assert tab.loc["x", "t_nw"] > 5
