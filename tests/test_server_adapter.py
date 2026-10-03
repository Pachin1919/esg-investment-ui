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
    assert sum(c["allocation"] for c in companies) == 100


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
