import numpy as np
import pandas as pd
import pytest

from esgx.factors.gmb import gmb_regression
from esgx.factors.timeseries import FF5_MOM
from esgx.portfolio.backtest import backtest, characterize
from esgx.portfolio.exposures import exposure_snapshot, green_exposures
from esgx.portfolio.optimize import factor_cov, factor_expected_returns, mean_variance_green
from esgx.portfolio.tilt import green_tilt, tilt_ladder


def _factors(months, seed=0):
    rng = np.random.default_rng(seed)
    T = len(months)
    return pd.DataFrame({
        "month": months,
        "mkt_rf": rng.normal(0.005, 0.04, T),
        "smb": rng.normal(0.0, 0.02, T),
        "hml": rng.normal(0.0, 0.02, T),
        "rmw": rng.normal(0.0, 0.02, T),
        "cma": rng.normal(0.0, 0.02, T),
        "mom": rng.normal(0.0, 0.02, T),
        "rf": 0.002,
    })


def _panel_with_gmb_betas(T=72, n_firms=5, seed=1):
    """Firm i earns b_i = 0.5*i on the GMB series plus a market loading and small noise."""
    rng = np.random.default_rng(seed)
    months = pd.period_range("2018-01", periods=T, freq="M")
    gmb = pd.DataFrame({"month": months, "gmb": rng.normal(0.001, 0.02, T)})
    factors = _factors(months, seed=seed + 1)
    f = factors.merge(gmb, on="month")
    rows = []
    for i in range(n_firms):
        b = 0.5 * i
        for t, m in enumerate(months):
            ret = 0.004 + b * f.loc[t, "gmb"] + 0.5 * f.loc[t, "mkt_rf"] + rng.normal(0, 0.005)
            rows.append({"firm_id": f"F{i}", "month": m, "ret": ret, "mktcap": 1e9})
    return pd.DataFrame(rows), factors, gmb


# --- exposures ---

def test_exposure_snapshot_recovers_gmb_betas():
    panel, factors, gmb = _panel_with_gmb_betas()
    snap = exposure_snapshot(panel, factors, gmb)
    for i in range(5):
        assert abs(snap.loc[f"F{i}", "b_gmb"] - 0.5 * i) < 0.1
    assert snap["t_alpha"].notna().all()


def test_green_exposures_rolling_warmup_and_shift():
    panel, factors, gmb = _panel_with_gmb_betas()
    exp = green_exposures(panel, factors, gmb, window=48, min_obs=36)
    per_firm = exp.groupby("firm_id")["b_gmb"]
    assert (per_firm.apply(lambda s: s.notna().sum()) == 72 - 36).all()  # warmup + 1-period shift
    last = exp.sort_values("month").groupby("firm_id").tail(1).set_index("firm_id")
    for i in range(5):
        assert abs(last.loc[f"F{i}", "b_gmb"] - 0.5 * i) < 0.15


# --- tilt ---

def _base_and_g(n=40):
    firms = [f"F{i}" for i in range(n)]
    base_w = pd.Series(1.0 / n, index=firms)
    g = pd.Series(np.linspace(-3.0, 0.0, n), index=firms)  # F(n-1) is greenest
    return base_w, g


def test_tilt_lam_zero_reproduces_index():
    base_w, g = _base_and_g()
    w = green_tilt(base_w, g, lam=0.0)
    assert np.allclose(w.values, base_w.values)
    assert abs(w.sum() - 1.0) < 1e-9


def test_tilt_higher_lam_is_greener_and_caps():
    base_w, g = _base_and_g()
    w1 = green_tilt(base_w, g, lam=1.0)
    assert w1["F39"] > w1["F0"]
    assert (w1 * g).sum() > (base_w * g).sum()
    w2 = green_tilt(base_w, g, lam=2.0, w_max=0.05)
    assert w2.max() <= 0.05 + 1e-9
    assert abs(w2.sum() - 1.0) < 1e-9


def test_tilt_ladder_monotone_greenness():
    base_w, g = _base_and_g()
    lad = tilt_ladder(base_w, g)
    assert lad["g_avg"].is_monotonic_increasing
    assert lad.loc[lad["lam"] == 0.0, "turnover"].iloc[0] < 1e-9


def test_tilt_guards():
    base_w, g = _base_and_g(n=10)
    with pytest.raises(ValueError, match="min_names"):
        green_tilt(base_w, g, lam=1.0, min_names=30)
    base_w, g = _base_and_g()
    g_missing = g.copy()
    g_missing.iloc[:5] = np.nan
    w = green_tilt(base_w, g_missing, lam=1.0, keep_unscored=False)
    assert len(w) == 35


# --- optimize ---

def _betas(n=30, seed=2):
    rng = np.random.default_rng(seed)
    cols = ["b_" + c for c in FF5_MOM] + ["b_gmb"]
    B = pd.DataFrame(rng.normal(0, 0.5, (n, len(cols))), columns=cols,
                     index=[f"F{i}" for i in range(n)])
    B["b_mkt_rf"] += 1.0
    return B


def test_factor_cov_symmetric_positive_diag():
    B = _betas()
    f_cols = FF5_MOM + ["gmb"]
    A = np.random.default_rng(3).normal(0, 0.02, (len(f_cols), len(f_cols)))
    f_cov = pd.DataFrame(A @ A.T, index=f_cols, columns=f_cols)
    S = factor_cov(B, f_cov, pd.Series(0.01, index=B.index))
    assert np.allclose(S, S.T)
    assert (np.diag(S) > 0).all()


def test_factor_expected_returns():
    B = _betas(n=3)
    f_mean = pd.Series({c: 0.0 for c in FF5_MOM + ["gmb"]})
    f_mean["mkt_rf"] = 0.01
    mu = factor_expected_returns(B, f_mean)
    assert np.allclose(mu.values, B["b_mkt_rf"].values * 0.01)


def test_mean_variance_green_tilts_toward_green():
    n = 20
    names = [f"F{i}" for i in range(n)]
    mu = pd.Series(0.0, index=names)
    cov = pd.DataFrame(np.eye(n) * 0.04, index=names, columns=names)
    g = pd.Series(np.linspace(-3.0, 0.0, n), index=names)
    w0 = mean_variance_green(mu, cov, g=g, lam=0.0)
    assert np.allclose(w0.values, 1.0 / n, atol=1e-4)
    w1 = mean_variance_green(mu, cov, g=g, lam=0.5, w_max=0.2)
    assert w1["F19"] > w1["F0"]
    assert abs(w1.sum() - 1.0) < 1e-6


# --- backtest / characterize ---

def test_backtest_known_returns_and_costs():
    months = pd.period_range("2024-01", periods=3, freq="M")
    weights = pd.DataFrame([
        {"month": m, "firm_id": f, "w": 0.5} for m in months for f in ["A", "B"]
    ])
    rets = {"A": [0.02, 0.01, -0.01], "B": [0.04, 0.03, 0.01]}
    panel = pd.DataFrame([
        {"month": m, "firm_id": f, "ret": r, "mktcap": 1e9}
        for f, rs in rets.items() for m, r in zip(months, rs)
    ])
    bt = backtest(weights, panel, cost_bps=0.0)
    assert np.allclose(bt["ret_gross"], [0.03, 0.02, 0.0])
    assert np.allclose(bt["turnover"], [0.5, 0.0, 0.0])  # build, then static weights
    bt_cost = backtest(weights, panel, cost_bps=100.0)
    assert abs(bt_cost.loc[0, "ret"] - (0.03 - 0.01 * 0.5)) < 1e-12
    assert np.allclose(bt_cost.loc[1:, "ret"], bt_cost.loc[1:, "ret_gross"])


def test_characterize_recovers_portfolio_gmb_beta():
    _, factors, gmb = _panel_with_gmb_betas(T=72)
    f = factors.merge(gmb, on="month")
    port_ret = pd.DataFrame({"month": f["month"], "ret": f["rf"] + 0.004 + 0.5 * f["gmb"]})
    bench = pd.DataFrame({"month": f["month"], "ret": f["rf"] + f["mkt_rf"]})
    out = characterize(port_ret, factors, bench_ret=bench, gmb=gmb)
    assert abs(out["b_gmb"] - 0.5) < 0.05
    for key in ["ann_ret", "ann_vol", "sharpe", "te", "ir", "alpha", "t_alpha", "r2"]:
        assert key in out


# --- gmb with controls ---

def test_gmb_regression_controls_remove_confounder():
    rng = np.random.default_rng(4)
    n, T = 150, 36
    months = pd.period_range("2018-01", periods=T, freq="M")
    g = rng.normal(-1.0, 1.0, n)
    s = 0.8 * g + rng.normal(0, 0.6, n)  # size proxy correlated with g
    factors = pd.DataFrame({"month": months, "mkt_rf": rng.normal(0, 0.02, T), "rf": 0.0})
    rows = []
    for t, m in enumerate(months):
        for i in range(n):
            rows.append({"firm_id": f"F{i}", "month": m, "g": g[i], "s": s[i],
                         "mktcap": 1e9,
                         "ret": 0.02 * g[i] + 0.03 * s[i] + factors.loc[t, "mkt_rf"]
                                + rng.normal(0, 0.02)})
    panel = pd.DataFrame(rows)
    raw = gmb_regression(panel, factors, window=24)["gmb_reg"].mean()
    ctl = gmb_regression(panel, factors, window=24, controls=["s"])["gmb_reg"].mean()
    assert raw > 0.03  # confounded: picks up the s effect through correlation with g
    assert abs(ctl - 0.02) < abs(raw - 0.02)
