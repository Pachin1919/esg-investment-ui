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
