import numpy as np
import pandas as pd
import pytest

from esgx.portfolio.optimize import mean_variance_green
from esgx.portfolio.recommend import GREEN_LAM, RISK_GAMMA, recommend


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
    assert out["params"]["gamma"] == RISK_GAMMA[1] == 12.0
    assert out["params"]["lam"] == GREEN_LAM[5] == 2.0
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
    assert sticky["turnover"] < free["turnover"]


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
