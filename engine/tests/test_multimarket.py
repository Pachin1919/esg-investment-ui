"""Pooled HK + TW recommendations: block factor model, base-currency returns, market="all"."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from esgx.api.main import app
from esgx.api.store import DataStore
from esgx.factors.timeseries import FF5_MOM
from esgx.portfolio.inputs import ModelInputs, combine_inputs, to_base_currency
from esgx.portfolio.optimize import factor_cov

T = 60
MONTHS = pd.period_range("2021-01", periods=T, freq="M")


def _part(suffix: str, n: int, mkt: np.ndarray, g_shift: float, seed: int) -> ModelInputs:
    rng = np.random.default_rng(seed)
    names = [f"F{i}.{suffix}" for i in range(n)]
    betas = pd.DataFrame({"b_mkt_rf": rng.normal(1, 0.1, n), "idio_var": 0.03**2, "alpha": 0.0}, index=names)
    g = pd.Series(np.linspace(-3, 0, n) + g_shift, index=names)
    return ModelInputs(betas, g, pd.DataFrame({"month": MONTHS, "mkt_rf": mkt}), ["mkt_rf"])


def _two_markets(rho: float) -> ModelInputs:
    rng = np.random.default_rng(1)
    a, e = rng.normal(0, 0.04, T), rng.normal(0, 0.04, T)
    b = rho * a + np.sqrt(1 - rho**2) * e
    return combine_inputs({"hk": _part("HK", 5, a, 0.0, 2), "tw": _part("TW", 8, b, -10.0, 3)})


def test_combine_builds_block_model():
    inp = _two_markets(rho=0.8)
    assert inp.cols == ["hk_mkt_rf", "tw_mkt_rf"] and len(inp.betas) == 13
    assert (inp.betas.loc[inp.betas.index.str.endswith(".HK"), "b_tw_mkt_rf"] == 0).all()
    assert (inp.betas.loc[inp.betas.index.str.endswith(".TW"), "b_hk_mkt_rf"] == 0).all()
    # greenness is standardized within market: the -10 level shift in TW must not survive pooling
    for sfx in (".HK", ".TW"):
        z = inp.g[inp.g.index.str.endswith(sfx)]
        assert z.mean() == pytest.approx(0.0, abs=1e-12) and z.std(ddof=0) == pytest.approx(1.0)
    _, f_cov = inp.moments()
    cov = factor_cov(inp.betas, f_cov, inp.betas["idio_var"])
    expect = inp.betas.loc["F0.HK", "b_hk_mkt_rf"] * f_cov.loc["hk_mkt_rf", "tw_mkt_rf"] * inp.betas.loc["F0.TW", "b_tw_mkt_rf"]
    assert cov.loc["F0.HK", "F0.TW"] == pytest.approx(expect)


def test_correlated_markets_diversify_less():
    def vol(rho: float) -> float:
        inp = _two_markets(rho)
        _, f_cov = inp.moments()
        cov = factor_cov(inp.betas, f_cov, inp.betas["idio_var"])
        w = pd.Series(1 / len(cov), index=cov.index)
        return float(np.sqrt(w @ cov @ w))

    assert vol(0.9) > vol(0.0) * 1.1


def test_gmb_dropped_when_joint_months_too_few():
    hk, tw = _part("HK", 4, np.zeros(T), 0.0, 0), _part("TW", 4, np.zeros(T), 0.0, 1)
    for part, lo in ((hk, 0), (tw, 40)):  # GMB months overlap on 20 rows only
        part.factors["mkt_rf"] = np.random.default_rng(lo).normal(0, 0.04, T)
        part.factors["gmb"] = np.where((np.arange(T) >= lo) & (np.arange(T) < lo + 40), 0.01, np.nan)
        part.betas["b_gmb"], part.cols = 0.2, ["mkt_rf", "gmb"]
    inp = combine_inputs({"hk": hk, "tw": tw})
    assert inp.cols == ["hk_mkt_rf", "tw_mkt_rf"] and inp.gmb_months == 0
    assert not [c for c in inp.betas.columns if c.endswith("gmb")]


def test_to_base_currency_compounds_fx_and_converts_mktcap():
    prices = pd.DataFrame({"firm_id": "1.TW", "month": ["2024-01", "2024-02", "2024-03"],
                           "ret": [0.10, 0.10, 0.10], "mktcap": [100.0, 100.0, 100.0]})
    fx = pd.DataFrame({"month": ["2024-01", "2024-02"], "pair": "TWDHKD", "rate": [0.25, 0.20]})
    out = to_base_currency(prices, fx)
    assert list(out["month"].astype(str)) == ["2024-02"]  # no FX return for Jan (first rate) or Mar (missing)
    assert out["ret"].iloc[0] == pytest.approx(1.10 * 0.8 - 1)  # TWD lost 20% against HKD
    assert out["mktcap"].iloc[0] == pytest.approx(20.0)


def _store(tmp_path, with_fx: bool = True) -> DataStore:
    out, raw = tmp_path / "o", tmp_path / "r"
    out.mkdir(), raw.mkdir()
    rng = np.random.default_rng(0)
    months = MONTHS.astype(str)
    common = rng.normal(0.004, 0.04, T)
    for market, region, sfx, n in (("hk", "asia_pacific_ex_japan", "HK", 12), ("tw", "emerging", "TW", 20)):
        fac = pd.DataFrame({"month": months, "rf": 0.002, **{c: rng.normal(0, 0.02, T) for c in FF5_MOM}})
        fac["mkt_rf"] = 0.7 * common + rng.normal(0, 0.02, T)
        fac.to_parquet(raw / f"factors_monthly_{region}.parquet")
        ids = [f"F{i:03d}.{sfx}" for i in range(n)]
        pd.DataFrame([{"firm_id": f, "month": m, "ret": 0.003 + 0.9 * fac.loc[t, "mkt_rf"] + rng.normal(0, 0.03),
                       "mktcap": 1e9} for f in ids for t, m in enumerate(months)]).to_parquet(raw / f"prices_monthly_{market}.parquet")
        pd.DataFrame({"firm_id": ids, "year": 2022, "provider": "walk_hard", "e_score": 5.0, "e_weight": 30.0,
                      "g": np.linspace(-3, 0, n), "g_across": 0.0, "g_within": 0.0}
                     ).to_csv(out / f"det_greenness_{market}.csv", index=False)
    if with_fx:
        pd.DataFrame({"month": months, "pair": "TWDHKD", "rate": 0.25 * np.cumprod(1 + rng.normal(0, 0.01, T))}
                     ).to_parquet(raw / "fx_monthly.parquet")
    return DataStore(outputs=out, processed=tmp_path / "p", raw=raw)


def _post(store: DataStore, **body) -> tuple[int, dict]:
    from esgx.api import portfolio_routes as pr

    app.dependency_overrides[pr._store] = lambda: store
    try:
        r = TestClient(app).post("/api/portfolio/recommend", json=body)
        return r.status_code, r.json()
    finally:
        app.dependency_overrides.clear()


def test_recommend_all_markets_trades_in_both(tmp_path):
    store = _store(tmp_path)
    code, d = _post(store, holdings={"F000.HK": 6000.0, "F001.HK": 4000.0}, market="all", pool="full",
                    risk_score=3, green_score=5, kappa=0.0, max_new_capital=5000.0)
    assert code == 200, d
    assert d["base_currency"] == "HKD" and d["params"]["n_candidates"] == 32
    assert d["markets"]["hk"]["n_modeled"] == 12 and d["markets"]["tw"]["n_modeled"] == 20
    buys = {t["market"] for t in d["trades"] if t["side"] == "buy"}
    assert buys == {"hk", "tw"}  # a HK-only portfolio is offered Taiwan names too
    assert sum(t["capital_delta"] for t in d["trades"]) == pytest.approx(5000.0, abs=1e-4)
    assert d["after"]["g_avg"] > d["before"]["g_avg"]
    code, one = _post(store, holdings={"F000.HK": 6000.0, "F001.HK": 4000.0}, market="hk", green_score=5, kappa=0.0)
    assert code == 200 and one["params"]["n_candidates"] == 12 and one["base_currency"] is None
    assert {t["market"] for t in one["trades"]} == {"hk"}


def test_recommend_all_markets_needs_fx(tmp_path):
    code, d = _post(_store(tmp_path, with_fx=False), holdings={"F000.HK": 100.0}, market="all")
    assert code == 503 and "TWDHKD" in d["detail"]


def test_industry_filter_and_filter_tree_across_markets(tmp_path):
    from esgx.api import portfolio_routes as pr

    store = _store(tmp_path)
    for name, sfx, n in (("universe_hsi", "HK", 12), ("universe_twse", "TW", 20)):
        pd.DataFrame({"firm_id": [f"F{i:03d}.{sfx}" for i in range(n)], "name": "Firm", "sector": "Tech",
                      "industry": ["Software" if i % 2 else "Chips" for i in range(n)], "country": sfx}
                     ).to_parquet(store.raw / f"{name}.parquet")
    code, d = _post(store, holdings={"F000.HK": 6000.0, "F001.TW": 4000.0}, market="all", pool="full", kappa=0.0,
                    filters={"include_industries": ["Software"]})
    assert code == 200, d
    assert d["screen"]["method"] == "filter" and d["screen"]["n_candidates"] == 16  # 6 HK + 10 TW
    row = {t["firm_id"]: t for t in d["trades"]}
    assert row["F000.HK"]["side"] == "hold (outside filter)"  # Chips holding kept, not sold
    assert {t["market"] for t in d["trades"] if t["side"] == "buy"} <= {"hk", "tw"}
    app.dependency_overrides[pr._store] = lambda: store
    try:
        tree = TestClient(app).get("/api/portfolio/filters", params={"market": "all", "pool": "full"}).json()
    finally:
        app.dependency_overrides.clear()
    assert tree["n_firms"] == 32


def test_largest_per_sector_takes_every_sector_first():
    from esgx.portfolio.pool import largest_per_sector

    caps = {"A1": 9.0, "A2": 8.0, "A3": 7.0, "B1": 2.0, "B2": 1.0, "C1": 0.5, "NEW": 99.0}
    prices = pd.DataFrame([{"firm_id": f, "month": m, "ret": 0.01, "mktcap": c}
                           for f, c in caps.items() for m in MONTHS[: 6 if f == "NEW" else 30].astype(str)])
    sectors = pd.Series({f: f[0] for f in caps if f != "NEW"})
    assert largest_per_sector(prices, sectors, 3) == ["A1", "B1", "C1"]  # one per sector before a second A
    assert largest_per_sector(prices, sectors, 4) == ["A1", "B1", "C1", "A2"]
    # NEW is the largest but has 6 months of returns: not eligible; a holding is added on top
    assert largest_per_sector(prices, sectors, 2, keep=["B2", "A1", "ZZ"]) == ["A1", "B1", "B2"]


def test_balanced_pool_matches_home_market_size(tmp_path):
    from esgx.api import portfolio_routes as pr

    store = _store(tmp_path)  # 12 HK + 20 TW priced names, no sectors -> the 12 first TW by cap
    code, d = _post(store, holdings={"F000.HK": 6000.0, "F019.TW": 4000.0}, market="all", kappa=0.0)
    assert code == 200, d
    assert d["pool"] == "balanced" and d["markets"]["hk"]["n_modeled"] == 12
    assert d["markets"]["tw"]["n_modeled"] == 13  # 12 = as many as HK, + the F019.TW holding
    assert d["unmodeled"] == [] and d["params"]["n_candidates"] == 25
    app.dependency_overrides[pr._store] = lambda: store
    try:
        tree = TestClient(app).get("/api/portfolio/filters", params={"market": "all"}).json()
    finally:
        app.dependency_overrides.clear()
    assert tree["n_firms"] == 0  # no universe files in this store; the count is over firms with a sector
