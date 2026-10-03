"""API contract tests on synthetic tables in a temp directory (no real data needed)."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from esgx.agents import pipeline as pl
from esgx.api.main import app, get_store
from esgx.api.store import DataStore, records


@pytest.fixture
def client(tmp_path):
    out, proc, raw = tmp_path / "outputs", tmp_path / "processed", tmp_path / "raw"
    for d in (out, proc, raw):
        d.mkdir()
    pd.DataFrame({"firm_id": ["0001.HK", "0002.HK"], "name": ["Alpha Holdings", "Beta Power"], "sector": ["Energy", "Utilities"],
                  "industry": ["Oil", "Electric"], "country": ["Hong Kong", "China"]}).to_parquet(raw / "universe_hsi.parquet")
    pd.DataFrame({"firm_id": ["1101.TW"], "name": ["TCC"], "sector": ["Cement"], "industry": ["Cement"],
                  "country": ["TW"]}).to_parquet(raw / "universe_twse.parquet")
    pd.DataFrame({"firm_id": ["1101.TW"], "year": [2025], "scope1": [410.0], "scope2": [80.0],
                  "scope3": [None], "source": ["twse_esg_openapi"], "matched": [True]}).to_parquet(proc / "emissions_tw.parquet")
    pd.DataFrame({"firm_id": ["1101.TW"], "year": [2025], "revenue": [50.0], "book_equity": [20.0]}).to_parquet(raw / "fundamentals_twse.parquet")
    pd.DataFrame({"firm_id": ["1101.TW"], "year": [2025], "provider": ["walk_hard"], "e_score": [2.0],
                  "e_weight": [50.0], "g": [-4.0], "g_across": [-3.0], "g_within": [-1.0]}).to_csv(out / "det_greenness_tw.csv", index=False)
    pd.DataFrame({"firm_id": ["0001.HK"], "year": [2023], "talk": [6.0], "walk": [2.0], "gap": [4.0], "n_docs": [1]}).to_csv(out / "talkwalk_firm_year_hk.csv", index=False)
    pd.DataFrame({"firm_id": ["0001.HK"], "form": ["esg_report"], "filing_date": ["2024-04-01"], "period": ["2023-12-31"], "accession": ["https://x/a1"],
                  "section": ["full_report"], "talk": [6.0], "walk": [2.0], "gap": [4.0], "glossiness": [1.2], "summary": ["s"]}).to_csv(out / "talkwalk_documents_hk.csv", index=False)
    pd.DataFrame({"firm_id": ["0001.HK", "0002.HK"], "year": [2023, 2023], "provider": ["walk_hard"] * 2, "e_score": [1.0, 9.0],
                  "e_weight": [50.0, 10.0], "g": [-4.5, -0.1], "g_across": [-4.0, -0.2], "g_within": [-0.5, 0.1]}).to_csv(out / "det_greenness_hk.csv", index=False)
    pd.DataFrame({"month": ["2020-01", "2020-02"], "gmb": [0.01, -0.005], "gmb_ew": [0.0, 0.0], "gmb_within": [0.002, 0.001], "n": [10, 10]}).to_csv(out / "gmb_monthly_hk.csv", index=False)
    pd.DataFrame({"firm_id": ["0001.HK", "0001.HK"], "year": [2022, 2023], "scope1": [100.0, 90.0], "scope2": [20.0, 20.0],
                  "scope3": [None, None], "source": ["hkex_esg_report"] * 2, "matched": [True, True]}).to_csv(out / "emissions_hk.csv", index=False)
    pd.DataFrame({"firm_id": ["0001.HK", "0001.HK"], "year": [2022, 2023], "revenue": [10.0, 10.0], "book_equity": [1.0, 1.0]}).to_parquet(raw / "fundamentals_yf_hk.parquet")
    store = DataStore(outputs=out, processed=proc, raw=raw)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_lists_datasets(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok"
    assert r["datasets"]["talkwalk_firm_year"]["available"] and r["datasets"]["talkwalk_firm_year"]["rows"] == 1
    assert r["datasets"]["emissions_hk"]["available"]
    assert not r["datasets"]["universe_hsci"]["available"]


def test_firms_flags(client):
    firms = {f["firm_id"]: f for f in client.get("/api/firms").json()}
    assert firms["0001.HK"]["has_talkwalk"] and firms["0001.HK"]["has_emissions"] and firms["0001.HK"]["has_greenness"]
    assert not firms["0002.HK"]["has_talkwalk"] and not firms["0002.HK"]["has_emissions"]


def test_firm_profile_and_404(client):
    p = client.get("/api/firms/0001.HK").json()
    assert p["name"] == "Alpha Holdings"
    assert [e["year"] for e in p["emissions"]] == [2022, 2023]
    assert p["emissions"][0]["scope12"] == 120.0 and p["emissions"][0]["intensity"] == 12.0
    assert p["emissions"][0]["scope3"] is None  # NaN -> null
    assert p["talkwalk"][0]["gap"] == 4.0
    assert p["documents"][0]["glossiness"] == 1.2
    assert client.get("/api/firms/ZZZ").status_code == 404


def test_greenness_defaults_and_sectors(client):
    g = client.get("/api/greenness").json()
    assert g["year"] == 2023 and g["provider"] == "walk_hard"
    assert g["firms"][0]["firm_id"] == "0001.HK"  # sorted brownest first
    sectors = {s["sector"]: s for s in g["sectors"]}
    assert sectors["Energy"]["n"] == 1 and sectors["Energy"]["g"] == -4.5


def test_gmb_cumulative_and_summary(client):
    g = client.get("/api/gmb").json()
    assert g["months"][1]["cum_gmb"] == pytest.approx(1.01 * 0.995 - 1)
    assert g["summary"]["gmb"]["n_months"] == 2


def test_search_and_documents_filter(client):
    assert client.get("/api/search", params={"q": "alp"}).json()[0]["firm_id"] == "0001.HK"
    assert client.get("/api/talkwalk/documents", params={"firm_id": "0002.HK"}).json() == []
    assert len(client.get("/api/talkwalk/documents").json()) == 1


def test_missing_files_degrade_to_empty(tmp_path):
    store = DataStore(outputs=tmp_path, processed=tmp_path, raw=tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    c = TestClient(app)
    assert c.get("/api/firms").json() == []
    assert c.get("/api/greenness").json()["firms"] == []
    assert c.get("/api/gmb").json()["months"] == []
    assert c.get("/api/talkwalk/firm-years").json() == []
    app.dependency_overrides.clear()


def test_records_converts_numpy_and_nan():
    df = pd.DataFrame({"a": [1, 2], "b": [1.5, float("nan")]})
    out = records(df)
    assert out == [{"a": 1, "b": 1.5}, {"a": 2, "b": None}]
    assert type(out[0]["a"]) is int


def test_api_pipeline_routes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from esgx.api.main import app

    monkeypatch.setattr(pl, "CONFIG_DIR", tmp_path / "cfg")
    c = TestClient(app)
    d = c.get("/api/pipeline/default").json()
    assert len(d["stages"]) == 10
    agents = c.get("/api/pipeline/agents").json()
    assert [a["id"] for a in agents] == [s["id"] for s in d["stages"]]
    assert all(t["name"] for a in agents for t in a["tools"])
    assert len(c.get("/api/pipeline/tools").json()) >= 20
    assert c.get("/api/method").json()["model"]
    r = c.post("/api/pipeline/configs", json={"name": "my test!", "spec": d})
    assert r.status_code == 200 and r.json()["saved"] == "my-test.json"
    assert c.get("/api/pipeline/configs").json()[0]["name"] == "default"
    est = c.post("/api/pipeline/estimate", json={"spec": d, "tickers": ["0005.HK", "1299.HK"]}).json()
    assert est["sections"] > 0 and est["total_usd"] > 0
    assert c.post("/api/pipeline/runs", json={"spec": d, "tickers": [], "mode": "dry_run"}).status_code == 400
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    assert c.post("/api/pipeline/runs", json={"spec": d, "tickers": ["0005.HK"], "mode": "live"}).status_code == 400


def _portfolio_store(tmp_path):
    """Store with synthetic prices, factors and greenness covering the GMB path."""
    out, proc, raw = tmp_path / "o2", tmp_path / "p2", tmp_path / "r2"
    for d in (out, proc, raw):
        d.mkdir()
    rng = np.random.default_rng(0)
    n, T = 35, 60
    months = pd.period_range("2021-01", periods=T, freq="M").astype(str)
    fac = pd.DataFrame({
        "month": months, "mkt_rf": rng.normal(0.004, 0.04, T), "smb": rng.normal(0, 0.02, T),
        "hml": rng.normal(0, 0.02, T), "rmw": rng.normal(0, 0.02, T), "cma": rng.normal(0, 0.02, T),
        "mom": rng.normal(0, 0.02, T), "rf": 0.002,
    })
    fac.to_parquet(raw / "factors_monthly_asia_pacific_ex_japan.parquet")
    rows = []
    for i in range(n):
        for t, m in enumerate(months):
            rows.append({"firm_id": f"F{i:03d}.HK", "month": m,
                         "ret": 0.004 + 0.9 * fac.loc[t, "mkt_rf"] + rng.normal(0, 0.03),
                         "mktcap": 1e9 * (1 + i / n)})
    pd.DataFrame(rows).to_parquet(raw / "prices_monthly_hk.parquet")
    green = pd.DataFrame({
        "firm_id": [f"F{i:03d}.HK" for i in range(n)] * 2,
        "year": [2021] * n + [2022] * n,
        "provider": "walk_hard",
        "e_score": [10 * i / (n - 1) for i in range(n)] * 2,
        "e_weight": 30.0,
        "g": [-3.0 * (1 - i / (n - 1)) for i in range(n)] * 2,
        "g_across": -1.5, "g_within": 0.0,
    })
    green.to_csv(out / "det_greenness_hk.csv", index=False)
    return DataStore(outputs=out, processed=proc, raw=raw)


def test_portfolio_recommend_needs_data(tmp_path):
    from esgx.api import portfolio_routes as pr

    store = DataStore(outputs=tmp_path / "o", processed=tmp_path / "p", raw=tmp_path / "r")
    app.dependency_overrides[pr._store] = lambda: store
    try:
        r = TestClient(app).post("/api/portfolio/recommend",
                                 json={"holdings": {"0001.HK": 100.0}})
        assert r.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_portfolio_recommend_end_to_end(tmp_path):
    from esgx.api import portfolio_routes as pr

    store = _portfolio_store(tmp_path)
    app.dependency_overrides[pr._store] = lambda: store
    try:
        c = TestClient(app)
        r = c.post("/api/portfolio/recommend", json={
            "holdings": {"F000.HK": 5000.0, "F001.HK": 3000.0, "UNKNOWN": 2000.0},
            "risk_score": 2, "green_score": 5, "kappa": 0.0,
        })
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["params"]["vol_target_ann"] == 0.12 and d["params"]["g_target_pctl"] == 0.9
        assert d["after"]["g_avg"] > d["before"]["g_avg"]
        assert d["after"]["b_gmb"] is not None  # GMB path active (35 names, 24+ months)
        assert d["coverage"]["n_modeled"] == 35 and d["coverage"]["gmb_months"] >= 24
        assert [u["firm_id"] for u in d["unmodeled"]] == ["UNKNOWN"]
        buys = [t for t in d["trades"] if t["side"] == "buy"]
        assert buys and all(t["capital_delta"] > 0 for t in buys)
        assert abs(sum(t["capital_delta"] for t in d["trades"])) < 1e-6
        assert c.post("/api/portfolio/recommend", json={"holdings": {"F000.HK": 1}, "risk_score": 9}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def _portfolio_store_with_universe(tmp_path):
    store = _portfolio_store(tmp_path)
    n = 35
    uni = pd.DataFrame({
        "firm_id": [f"F{i:03d}.HK" for i in range(n)],
        "name": [f"Firm {i:03d}" for i in range(n)],
        "sector": ["Energy"] * 17 + ["Tech"] * 18,
        "industry": ["Oil & Gas"] * 17 + ["Software"] * 18,
        "country": "Hong Kong",
    })
    uni.to_parquet(store.raw / "universe_hsi.parquet")
    return store


def test_portfolio_recommend_with_preferences_keyword_screen(tmp_path, monkeypatch):
    from esgx.api import portfolio_routes as pr

    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    store = _portfolio_store_with_universe(tmp_path)
    app.dependency_overrides[pr._store] = lambda: store
    try:
        c = TestClient(app)
        r = c.post("/api/portfolio/recommend", json={
            "holdings": {"F000.HK": 5000.0, "F020.HK": 5000.0},
            "risk_score": 3, "green_score": 4, "preferences": "tech", "kappa": 0.0,
        })
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["screen"]["method"] == "keyword" and d["screen"]["n_candidates"] == 18
        row = {t["firm_id"]: t for t in d["trades"]}
        assert row["F000.HK"]["side"] == "sell (outside preferences)" and row["F000.HK"]["w_target"] == 0
        assert all(t["firm_id"] >= "F017" for t in d["trades"] if t["side"] == "buy")
        r2 = c.post("/api/portfolio/recommend", json={
            "holdings": {"F000.HK": 1000.0}, "preferences": "xyz-no-such-sector"})
        assert r2.status_code == 200  # no filterable preference -> full universe, screen spec empty
        assert r2.json()["screen"]["n_candidates"] == 35
    finally:
        app.dependency_overrides.clear()


def test_portfolio_recommend_with_industry_filter(tmp_path, monkeypatch):
    from esgx.api import portfolio_routes as pr
    from esgx.portfolio import screen

    def no_llm(*a, **k):
        raise AssertionError("the structured filter must never call a model")

    monkeypatch.setattr(screen.llm, "parse", no_llm)
    store = _portfolio_store_with_universe(tmp_path)
    app.dependency_overrides[pr._store] = lambda: store
    try:
        c = TestClient(app)
        opts = c.get("/api/portfolio/filters").json()
        assert opts["n_firms"] == 35
        assert {s["sector"]: s["n"] for s in opts["sectors"]} == {"Energy": 17, "Tech": 18}
        assert opts["sectors"][1]["industries"] == [{"industry": "Software", "n": 18}]
        body = {"holdings": {"F000.HK": 5000.0, "F020.HK": 5000.0}, "risk_score": 3, "green_score": 4,
                "kappa": 0.0, "filters": {"include_industries": ["Software", "No Such Industry"]}}
        r = c.post("/api/portfolio/recommend", json=body)
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["screen"]["method"] == "filter" and d["screen"]["n_candidates"] == 18
        assert d["screen"]["spec"]["include_industries"] == ["Software"]  # unknown value dropped
        row = {t["firm_id"]: t for t in d["trades"]}
        # the holding outside the filter is left untouched; only filtered names are traded
        assert row["F000.HK"]["side"] == "hold (outside filter)"
        assert row["F000.HK"]["w_target"] == row["F000.HK"]["w_current"] == 0.5
        assert all(t["firm_id"] >= "F017" for t in d["trades"] if t["side"] in ("buy", "sell"))
        assert sum(t["w_target"] for t in d["trades"]) == pytest.approx(1.0, abs=1e-6)
        assert c.post("/api/portfolio/recommend", json=body).json()["trades"] == d["trades"]  # deterministic
        body["filters"] = {"exclude_sectors": ["Energy", "Tech"]}
        assert c.post("/api/portfolio/recommend", json=body).status_code == 400  # nothing left
    finally:
        app.dependency_overrides.clear()


def test_taiwan_is_served(client):
    # the other session's "no taiwan" was the API wiring, not the bucket: TW tables must be visible
    firms = {f["firm_id"]: f for f in client.get("/api/firms").json()}
    assert "1101.TW" in firms
    g = client.get("/api/greenness", params={"market": "tw"}).json()
    assert g["year"] == 2025 and g["firms"][0]["firm_id"] == "1101.TW"
    hk = client.get("/api/greenness").json()  # default stays HK
    assert hk["firms"][0]["firm_id"] == "0001.HK"
    p = client.get("/api/firms/1101.TW").json()
    assert p["emissions"][0]["scope12"] == 490.0 and p["emissions"][0]["intensity"] == 9.8
    assert p["greenness"][0]["g"] == -4.0
    assert client.get("/api/gmb", params={"market": "tw"}).json()["months"] == []  # no file -> empty, not an error
