"""API contract tests on synthetic tables in a temp directory (no real data needed)."""

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
