import numpy as np
import pandas as pd
import pytest

from esgx.portfolio.optimize import (
    mean_variance_green,
    mean_variance_green_target_vol,
    mean_variance_green_targets,
)
from esgx.portfolio.recommend import RISK_VOL, recommend


def _inputs(n=12, seed=0):
    rng = np.random.default_rng(seed)
    names = [f"F{i}" for i in range(n)]
    betas = pd.DataFrame({"b_mkt_rf": rng.normal(1, 0.2, n), "b_gmb": rng.normal(0, 0.5, n)}, index=names)
    f_mean = pd.Series({"mkt_rf": 0.005, "gmb": 0.001})
    f_cov = pd.DataFrame(np.diag([0.04**2, 0.02**2]), index=["mkt_rf", "gmb"], columns=["mkt_rf", "gmb"])
    idio = pd.Series(0.03**2, index=names)
    g = pd.Series(np.linspace(-3, 0, n), index=names)  # F0 brownest, F(n-1) greenest
    return betas, g, f_mean, f_cov, idio


def test_score_maps_and_validation():
    betas, g, f_mean, f_cov, idio = _inputs()
    out = recommend({"F0": 600.0, "F1": 400.0}, betas, g, f_mean, f_cov, idio, risk_score=1, green_score=5)
    assert out["params"]["vol_target_ann"] == RISK_VOL[1] == 0.08
    assert out["params"]["g_target_pctl"] == 0.9  # green_score=5 -> top decile
    with pytest.raises(ValueError, match="1-5"):
        recommend({"F0": 1.0}, betas, g, f_mean, f_cov, idio, risk_score=0)
    with pytest.raises(ValueError, match="1-5"):
        recommend({"F0": 1.0}, betas, g, f_mean, f_cov, idio, green_score=6)
    with pytest.raises(ValueError, match="positive total"):
        recommend({}, betas, g, f_mean, f_cov, idio)


def test_green_score_five_makes_portfolio_greener():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 3000.0, "F2": 2000.0}  # brown end
    out = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=5, kappa=0.0)
    assert out["after"]["g_avg"] > out["before"]["g_avg"]
    assert out["trades"]["w_target"].sum() == pytest.approx(1.0)
    assert out["trades"]["capital_delta"].sum() == pytest.approx(0.0, abs=1e-6)  # buys fund sells
    assert (out["trades"]["capital_delta"] > 0).any()


def test_turnover_penalty_keeps_current_portfolio():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 3000.0, "F2": 2000.0}
    free = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=5, kappa=0.0)
    sticky = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=5, kappa=1.0)
    # with anchored targets the same green/vol targets bind either way: kappa prices the
    # composition of trades but must never add turnover
    assert sticky["turnover"] <= free["turnover"] + 1e-6


def test_unmodeled_holdings_frozen_and_reported():
    betas, g, f_mean, f_cov, idio = _inputs()
    out = recommend({"F0": 5000.0, "XX9.HK": 5000.0}, betas, g, f_mean, f_cov, idio, green_score=4)
    assert [u["firm_id"] for u in out["unmodeled"]] == ["XX9.HK"]
    row = out["trades"].set_index("firm_id").loc["XX9.HK"]
    assert row["side"] == "frozen (unmodeled)" and row["dw"] == 0
    assert out["weights"].sum() == pytest.approx(0.5)  # modeled half optimized to 1 - w_frozen
    with pytest.raises(ValueError, match="nothing to optimize"):
        recommend({"XX9.HK": 100.0}, betas, g, f_mean, f_cov, idio)


def test_mean_variance_green_w0_kappa():
    n = 10
    names = [f"F{i}" for i in range(n)]
    mu = pd.Series(0.0, index=names)
    cov = pd.DataFrame(np.eye(n) * 0.04, index=names, columns=names)
    g = pd.Series(np.linspace(-2, 0, n), index=names)
    w0 = pd.Series(0.0, index=names)
    w0["F0"] = 1.0  # all in the brownest name
    free = mean_variance_green(mu, cov, g=g, lam=0.5, w_max=0.2, w0=w0, kappa=0.0)
    sticky = mean_variance_green(mu, cov, g=g, lam=0.5, w_max=0.2, w0=w0, kappa=1.0)
    assert sticky["F0"] > free["F0"]  # the penalty defends the current position
    assert sticky.sum() == pytest.approx(1.0)


def test_universe_subset_sells_outside_preferences():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 5000.0}
    subset = [f"F{i}" for i in range(6, 12)]  # green half, excludes the holdings
    out = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=4, kappa=0.0,
                    w_max=0.2, universe=subset)
    row = out["trades"].set_index("firm_id")
    assert row.loc["F0", "side"] == "sell (outside preferences)" and row.loc["F0", "w_target"] == 0
    assert set(out["weights"].index) == set(subset)
    assert out["params"]["n_candidates"] == 6
    assert out["trades"]["w_target"].sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="no candidate"):
        recommend(holdings, betas, g, f_mean, f_cov, idio, universe=["NOPE"])


def test_new_capital_budget_sizes_target_and_nets_to_injection():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 3000.0, "F2": 2000.0}  # 10k current capital
    out = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=4, kappa=0.0,
                    max_new_capital=20000.0)
    assert out["total_capital"] == 10000.0
    assert out["new_capital"] == 20000.0
    assert out["target_capital"] == 30000.0
    # the injection is the net of the trade list, and never exceeds the budget
    assert out["trades"]["capital_delta"].sum() == pytest.approx(20000.0, abs=1e-4)
    assert out["trades"]["w_target"].sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="max_new_capital"):
        recommend(holdings, betas, g, f_mean, f_cov, idio, max_new_capital=-1.0)


def test_risk_score_orders_realized_volatility():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 5000.0}
    cautious = recommend(holdings, betas, g, f_mean, f_cov, idio, risk_score=1, kappa=0.0)
    aggressive = recommend(holdings, betas, g, f_mean, f_cov, idio, risk_score=5, kappa=0.0)
    assert cautious["after"]["ann_vol"] < aggressive["after"]["ann_vol"]
    assert cautious["params"]["vol_target_ann"] == 0.08
    assert aggressive["params"]["vol_target_ann"] == 0.25
    assert cautious["params"]["gamma"] > aggressive["params"]["gamma"]


def test_green_score_orders_realized_greenness():
    betas, g, f_mean, f_cov, idio = _inputs()
    holdings = {"F0": 5000.0, "F1": 5000.0}
    light = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=2, kappa=0.0)
    deep = recommend(holdings, betas, g, f_mean, f_cov, idio, green_score=5, kappa=0.0)
    assert light["after"]["g_avg"] < deep["after"]["g_avg"]
    assert light["params"]["g_target_pctl"] == 0.60 and deep["params"]["g_target_pctl"] == 0.90


def test_targets_solver_hits_green_anchor_and_clamps():
    n = 12
    names = [f"F{i}" for i in range(n)]
    rng = np.random.default_rng(1)
    mu = pd.Series(rng.normal(0.004, 0.002, n), index=names)
    cov = pd.DataFrame(np.diag(np.linspace(0.01, 0.09, n)), index=names, columns=names)
    g = pd.Series(np.linspace(-3, 0, n)[rng.permutation(n)], index=names)  # shuffled: risk and green targets don't systematically conflict
    w, _, _ = mean_variance_green_targets(mu, cov, g=g, vol_target=0.25, g_target=-1.0, w_max=0.15)
    assert abs(float(w.to_numpy() @ g.to_numpy()) - (-1.0)) < 0.15
    # unreachably green target: clamps at the greenest allowed portfolio instead of failing
    w_cap, _, _ = mean_variance_green_targets(mu, cov, g=g, vol_target=0.25, g_target=5.0, w_max=0.15)
    assert float(w_cap.to_numpy() @ g.to_numpy()) >= float(w.to_numpy() @ g.to_numpy())


def test_target_vol_bisection_hits_and_clamps():
    n = 10
    names = [f"F{i}" for i in range(n)]
    mu = pd.Series(0.0, index=names)
    cov = pd.DataFrame(np.diag(np.linspace(0.01, 0.09, n)), index=names, columns=names)
    w, gamma = mean_variance_green_target_vol(mu, cov, vol_target=0.22, w_max=0.2)
    S = cov.to_numpy()
    ann = float(np.sqrt(12 * w @ S @ w))
    assert ann == pytest.approx(0.22, abs=0.01)
    # below the achievable floor: clamps to the min-variance portfolio instead of failing
    w_min, gamma_min = mean_variance_green_target_vol(mu, cov, vol_target=0.05, w_max=0.2)
    assert gamma_min >= gamma
    assert float(np.sqrt(12 * w_min @ S @ w_min)) <= ann
