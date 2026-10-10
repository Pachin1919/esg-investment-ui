"""Currency and availability regressions using synthetic data, with no network calls."""

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from esgx.api import portfolio_routes
from esgx.api.portfolio_routes import _last_close, _usd_rates
from esgx.api.store import DataStore
from esgx.factors.timeseries import FF5_MOM
from esgx.measures.carbon import align_annual_to_months
from esgx.portfolio.inputs import market_inputs, to_base_currency
from esgx.portfolio.positions import add_positions


def _store(tmp_path, with_fx=True):
    raw, out = tmp_path / "raw", tmp_path / "outputs"
    raw.mkdir()
    out.mkdir()
    rng = np.random.default_rng(33)
    months = pd.period_range("2021-01", "2025-12", freq="M").astype(str)
    for market, region, suffix in [("hk", "asia_pacific_ex_japan", "HK"), ("tw", "emerging", "TW")]:
        factors = pd.DataFrame({"month": months, "rf": 0.002,
                                **{c: rng.normal(0, 0.02, 60) for c in FF5_MOM}})
        factors.to_parquet(raw / f"factors_monthly_{region}.parquet")
        ids = [f"F{i:03d}.{suffix}" for i in range(12)]
        pd.DataFrame([{"firm_id": fid, "month": month, "ret": 0.002 + factors.iloc[t]["mkt_rf"] + rng.normal(0, 0.03),
                       "mktcap": 1e9} for fid in ids for t, month in enumerate(months)]).to_parquet(raw / f"prices_monthly_{market}.parquet")
        pd.DataFrame({"firm_id": ids, "year": 2022, "g": np.linspace(-3, 0, 12)}).to_csv(out / f"det_greenness_{market}.csv", index=False)
    if with_fx:
        pd.concat([pd.DataFrame({"month": months, "pair": "USDHKD", "rate": 7.8}),
                   pd.DataFrame({"month": months, "pair": "TWDHKD", "rate": 0.25})], ignore_index=True).to_parquet(raw / "fx_monthly.parquet")
    return DataStore(raw=raw, outputs=out, processed=tmp_path / "processed")


def _post(store, **body):
    app = FastAPI()
    app.include_router(portfolio_routes.router)
    app.dependency_overrides[portfolio_routes._store] = lambda: store
    response = TestClient(app).post("/api/portfolio/recommend", json=body)
    return response.status_code, response.json()


def test_fx_gap_is_not_a_one_month_return():
    prices = pd.DataFrame({"firm_id": "A", "month": ["2024-03", "2024-04"],
                           "ret": 0.1, "mktcap": 100.0})
    fx = pd.DataFrame({"month": ["2024-01", "2024-03", "2024-04"], "rate": [1.0, 1.2, 1.3]})
    converted = to_base_currency(prices, fx)
    assert list(converted["month"].astype(str)) == ["2024-04"]
    assert converted.iloc[0]["ret"] == pytest.approx(1.1 * 1.3 / 1.2 - 1)


@pytest.mark.parametrize("rates", [[1.0, 0.0], [1.0, -1.0], [1.0, np.nan]])
def test_invalid_fx_is_rejected(rates):
    prices = pd.DataFrame({"firm_id": "A", "month": ["2024-01", "2024-02"], "ret": 0.0, "mktcap": 1.0})
    fx = pd.DataFrame({"month": ["2024-01", "2024-02"], "rate": rates})
    with pytest.raises(ValueError, match="positive"):
        to_base_currency(prices, fx)


def test_cross_rates_match_quote_direction(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"month": ["2024-01", "2024-01"], "pair": ["TWDHKD", "USDHKD"],
                  "rate": [0.25, 8.0]}).to_parquet(raw / "fx_monthly.parquet")
    store = DataStore(raw=raw)
    assert _usd_rates(store, "tw")["rate"].iloc[0] == pytest.approx(0.25 / 8)
    assert _usd_rates(store, "hk")["rate"].iloc[0] == pytest.approx(1 / 8)


def _known_usd_model():
    rng = np.random.default_rng(123)
    months = pd.period_range("2021-01", periods=60, freq="M")
    fac = pd.DataFrame({"month": months, "rf": 0.002, **{c: rng.normal(0.0, 0.025, len(months)) for c in FF5_MOM}})
    fx = pd.DataFrame({"month": pd.period_range("2020-12", periods=61, freq="M"),
                       "rate": 0.03 * np.cumprod(1 + rng.normal(0, 0.02, 61))})
    fx_return = fx["rate"].pct_change().iloc[1:].to_numpy()
    usd_return = 0.002 + 1.4 * fac["mkt_rf"].to_numpy() - 0.3 * fac["hml"].to_numpy()
    local_return = (1 + usd_return) / (1 + fx_return) - 1
    px = pd.DataFrame({"month": months, "firm_id": "A.TW", "ret": local_return, "mktcap": 1e9})
    green = pd.DataFrame({"firm_id": ["A.TW", "A.TW"], "year": [2021, 2025], "g": [-1.0, 99.0]})
    return px, fx, fac, green


def test_local_returns_are_usd_before_us_rf_regression_and_future_g_excluded():
    prices, fx, factors, green = _known_usd_model()
    inputs = market_inputs(to_base_currency(prices, fx), factors, green)
    assert inputs.betas.loc["A.TW", "b_mkt_rf"] == pytest.approx(1.4)
    assert inputs.betas.loc["A.TW", "b_hml"] == pytest.approx(-0.3)
    assert inputs.betas.loc["A.TW", "alpha"] == pytest.approx(0.0, abs=1e-12)
    assert inputs.g["A.TW"] == -1.0  # year 2025 is unavailable before July 2026


def test_percent_like_factors_are_rejected_without_rescaling():
    prices, fx, factors, green = _known_usd_model()
    factors.loc[0, "mkt_rf"] = 2.5  # 250% decimal; likely percent units, never silently guessed
    with pytest.raises(ValueError, match="decimal"):
        market_inputs(to_base_currency(prices, fx), factors, green)


def test_scored_coverage_excludes_unpriced_source_firms(tmp_path):
    store = _store(tmp_path)
    path = store.outputs / "det_greenness_hk.csv"
    green = pd.read_csv(path)
    pd.concat([green, pd.DataFrame({"firm_id": ["UNPRICED.HK"], "year": [2022], "g": [100.0]})],
              ignore_index=True).to_csv(path, index=False)
    status, data = _post(store, holdings={"F000.HK": 100}, market="all")
    assert status == 200, data
    assert data["markets"]["hk"]["n_scored"] == data["markets"]["hk"]["n_modeled"] == 12
    assert data["coverage"]["n_scored"] == 24


def test_annual_fallback_july_boundary_and_explicit_lag():
    annual = pd.DataFrame({"firm_id": ["A", "A"], "year": [2023, 2024], "g": [1.0, 2.0]})
    months = pd.period_range("2024-06", "2025-07", freq="M")
    expanded = align_annual_to_months(annual, months).set_index("month")
    assert pd.Period("2024-06") not in expanded.index
    assert expanded.loc[pd.Period("2024-07"), "g"] == 1.0
    assert expanded.loc[pd.Period("2025-06"), "g"] == 1.0
    assert expanded.loc[pd.Period("2025-07"), "g"] == 2.0
    lagged = align_annual_to_months(annual, months, lag_months=18)
    assert str(lagged["month"].min()) == "2025-06"  # explicit Dec+18 semantics preserved


def test_actual_availability_overrides_fallback_without_within_month_lookahead():
    annual = pd.DataFrame({"firm_id": ["A"], "year": [2023], "g": [1.0], "available_date": ["2024-10-15"]})
    months = pd.period_range("2024-07", "2024-12", freq="M")
    expanded = align_annual_to_months(annual, months)
    assert list(expanded["month"].astype(str)) == ["2024-11", "2024-12"]
    assert align_annual_to_months(annual.iloc[:0], months).empty


def test_single_taiwan_prices_use_hkd_capital_and_no_future_fx(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"firm_id": ["A.TW"], "date": ["2024-02-15"], "close": [100.0]}).to_parquet(raw / "last_close_tw.parquet")
    pd.DataFrame({"month": ["2024-01", "2024-02", "2025-01"], "pair": "TWDHKD",
                  "rate": [0.25, 0.3, 0.5]}).to_parquet(raw / "fx_monthly.parquet")
    close = _last_close(DataStore(raw=raw), ["tw"])
    trades = add_positions(pd.DataFrame({"firm_id": ["A.TW"], "w_current": [1.0], "w_target": [1.0]}), 1000, close)
    assert close["A.TW"] == 25.0
    assert trades["shares_current"].iloc[0] == 40
    assert close.attrs["timing"]["tw"] == {"price_date": "2024-02-15", "fx_month": "2024-01"}


def test_foreign_close_without_date_does_not_guess_shares(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"firm_id": ["A.TW"], "close": [100.0]}).to_parquet(raw / "last_close_tw.parquet")
    pd.DataFrame({"month": ["2024-01"], "pair": "TWDHKD", "rate": [0.25]}).to_parquet(raw / "fx_monthly.parquet")
    assert _last_close(DataStore(raw=raw), ["tw"]).empty


def test_single_market_requires_usd_fx_and_explicit_hkd_capital(tmp_path):
    store = _store(tmp_path, with_fx=False)
    status, data = _post(store, holdings={"F000.HK": 100}, market="hk")
    assert status == 503 and "USDHKD" in data["detail"]
    status, _ = _post(store, holdings={"F000.HK": 100}, capital_currency="TWD")
    assert status == 422


def test_recommendation_exposes_regional_proxy_and_model_period(tmp_path):
    store = _store(tmp_path)
    store.dataset_id = "snapshot-under-test"
    status, data = _post(store, holdings={"F000.HK": 100}, market="all")
    assert status == 200, data
    assert data["dataset_id"] == "snapshot-under-test"
    assert data["model_period"] == {"start": "2021-02", "end": "2025-12", "n_months": 59}
    assert data["markets"]["hk"]["factor_region"] == "asia_pacific_ex_japan"
    assert data["markets"]["tw"]["factor_region"] == "emerging"
    assert data["markets"]["tw"]["listing_currency"] == "TWD"
    assert all(t["price_currency"] == "HKD" for t in data["trades"])
