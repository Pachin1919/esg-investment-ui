"""Tests for the server and communication adapter layer."""

import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.adapter import format_company_for_ui, dataframe_to_companies
import pandas as pd


@pytest.fixture
def client():
    return TestClient(app)


def test_format_company_preserves_missing_as_none():
    row = pd.Series({
        "firm_id": "TEST",
        "name": "Test Company",
        "ticker": "TST",
        "sector": "Tech",
        "country": "Hong Kong",
        "e_score": None,
        "e_weight": 25.0,
        "carbon": None,
        "walk": None,
        "talk": None,
    })
    c = format_company_for_ui(row)
    assert c["score"] is None
    assert c["carbon"] is None
    assert c["walk"] is None
    assert c["talk"] is None
    assert c["materiality"] == 25


def test_api_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["capabilities"]["liveData"] is True


def test_api_companies(client):
    r = client.get("/api/companies")
    assert r.status_code == 200
    companies = r.json()
    assert len(companies) >= 5
    # Total allocations should sum to 100%
    assert sum(c["allocation"] for c in companies) == pytest.approx(100)


def test_api_portfolio_analyze(client):
    payload = {
        "allocations": {
            "0002-hk": 50.0,
            "0066-hk": 50.0,
        }
    }
    r = client.post("/api/portfolio/analyze", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["total_allocation"] == 100.0
    assert res["coverage_pct"] == 100
    assert res["portfolio_greenness"] is not None


def test_api_sample_csv(client):
    r = client.get("/api/portfolio/sample-csv")
    assert r.status_code == 200
    assert "ticker,allocation" in r.text
    assert "0002.HK" in r.text


def test_api_upload_csv(client):
    csv_text = "ticker,allocation\n0002.HK,40\n0066.HK,60\n"
    r = client.post("/api/portfolio/upload-csv", json={"csv_text": csv_text})
    assert r.status_code == 200
    data = r.json()
    assert data["total_allocation"] == 100.0
    assert len(data["companies"]) == 2
    assert data["companies"][0]["ticker"] == "0002.HK"
    assert data["companies"][0]["allocation"] == 40.0


def test_api_companies_one_scored_row_per_firm(client):
    companies = client.get("/api/companies?market=hk").json()
    ids = [c["id"] for c in companies]
    assert len(ids) == len(set(ids))
    assert all(c["region"] != "nan" and c["name"] != "nan" for c in companies)
    # every firm with a walk score carries the same number as its E_score (E_score IS walk)
    assert all(c["score"] == c["walk"] for c in companies if c["walk"] is not None)


def test_firms_with_greenness_only_are_listed(tmp_path, monkeypatch):
    """A market whose greenwashing table covers few firms still lists every firm with greenness."""
    from server import dataset

    out, raw = tmp_path / "outputs", tmp_path / "raw"
    out.mkdir(), raw.mkdir()
    monkeypatch.setattr(dataset, "OUTPUT_DIR", out)
    monkeypatch.setattr(dataset, "RAW_DIR", raw)
    pd.DataFrame({"firm_id": ["1101.TW"], "year": [2025], "sector": ["Cement"], "greenwasher": [1], "greenhusher": [0],
                  "talk": [10.0], "walk": [1.7], "gap": [8.3]}).to_csv(out / "det_greenwashing_tw.csv", index=False)
    pd.DataFrame({"firm_id": ["1101.TW", "2330.TW", "2330.TW"], "year": [2025, 2024, 2025],
                  "e_score": [3.0, 6.0, 7.0], "e_weight": [40.0, 30.0, 30.0]}).to_csv(out / "det_greenness_tw.csv", index=False)
    pd.DataFrame({"firm_id": ["1101.TW", "2330.TW"], "name": ["TCC", "TSMC"],
                  "sector": ["Cement", "Semiconductor"]}).to_parquet(raw / "universe_twse.parquet")
    pd.DataFrame({"firm_id": ["1101.TW", "2330.TW", "2330.TW"], "year": [2025, 2024, 2025],
                  "walk": [9.9, 1.0, 6.5], "walk_intensity_level": [9.9, 1.0, 6.0]}).to_csv(out / "det_walk_tw.csv", index=False)
    df = dataset.load_market("tw").set_index("firm_id")
    assert list(df.index) == ["1101.TW", "2330.TW"]
    assert df.loc["1101.TW", "walk"] == 1.7  # the greenwashing row keeps its own walk
    assert df.loc["1101.TW", "talk"] == 10.0 and df.loc["1101.TW", "e_score"] == 3.0
    tsmc = format_company_for_ui(df.reset_index().iloc[1])
    assert tsmc["name"] == "TSMC" and tsmc["sector"] == "Semiconductor" and tsmc["region"] == "Taiwan"
    assert tsmc["score"] == 7.0  # latest greenness year
    assert tsmc["walk"] == 6.5 and tsmc["carbon"] == 6.0  # walk table, same year as the greenness row
    assert tsmc["talk"] is None and tsmc["gap"] is None and tsmc["greenwasher"] is False
    (out / "det_greenwashing_tw.csv").unlink()
    assert len(dataset.load_market("tw")) == 2  # greenness alone is enough
    (out / "det_greenness_tw.csv").unlink()
    assert dataset.load_market("tw") is None
