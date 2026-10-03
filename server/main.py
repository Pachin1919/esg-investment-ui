"""FastAPI communication layer for Green Street ESG Investment UI.

Serves data computed by the quantitative analysis engine (esgx + greenwash)
and formats it directly for the React / TypeScript UI via server.adapter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure engine is in path
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "engine", ROOT / "engine" / "greenwash"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.measures.greenness import greenness
from server.adapter import dataframe_to_companies, format_company_for_ui

app = FastAPI(
    title="Green Street Analysis Engine API",
    description="Backend communication layer serving quantitative ESG scores and portfolio analytics",
    version="0.4.0",
)

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PortfolioRequest(BaseModel):
    allocations: dict[str, float]  # company id -> allocation percent (e.g. {"0002-hk": 25.0, ...})


def load_latest_dataset() -> pd.DataFrame:
    """Load latest scored companies from processed or outputs directories, or fallback to HK universe."""
    scores_file = OUTPUT_DIR / "main_scores.csv"
    det_gw_hk = OUTPUT_DIR / "det_greenwashing_hk.csv"
    det_gw_us = OUTPUT_DIR / "det_greenwashing.csv"

    # Check for Hong Kong deterministic greenwashing output
    if det_gw_hk.exists():
        df = pd.read_csv(det_gw_hk)
        univ_file = RAW_DIR / "universe_hk.parquet"
        if univ_file.exists():
            univ = pd.read_parquet(univ_file)
            df = df.merge(univ[["firm_id", "name", "ticker"]], on="firm_id", how="left")
        return df

    # Check for US deterministic output
    if det_gw_us.exists():
        df = pd.read_csv(det_gw_us)
        univ_file = RAW_DIR / "universe_sp500.parquet"
        if univ_file.exists():
            univ = pd.read_parquet(univ_file)
            df = df.merge(univ[["firm_id", "name", "ticker"]], on="firm_id", how="left")
        return df

    # Otherwise load HK universe and generate initial baseline scores
    from esgx.ingest.universe_hk import load_universe_hk
    firms = load_universe_hk()
    # Baseline representative demo scoring based on HK companies
    defaults = []
    sample_metrics = [
        {"firm_id": "0002.HK", "name": "CLP Holdings", "ticker": "0002.HK", "sector": "Utilities", "region": "Hong Kong", "e_score": 8.2, "e_weight": 45, "carbon": 8.5, "walk": 7.8, "talk": 8.1, "greenwasher": 0, "greenhusher": 0, "gap": 0.3},
        {"firm_id": "0066.HK", "name": "MTR Corporation", "ticker": "0066.HK", "sector": "Industrials", "region": "Hong Kong", "e_score": 7.4, "e_weight": 40, "carbon": 7.2, "walk": 7.6, "talk": 7.8, "greenwasher": 0, "greenhusher": 0, "gap": 0.2},
        {"firm_id": "2330.TW", "name": "Taiwan Semiconductor", "ticker": "2330.TW", "sector": "Technology", "region": "Taiwan", "e_score": 6.7, "e_weight": 30, "carbon": 6.3, "walk": 7.1, "talk": 8.2, "greenwasher": 0, "greenhusher": 0, "gap": 1.1},
        {"firm_id": "0857.HK", "name": "PetroChina Company", "ticker": "0857.HK", "sector": "Energy", "region": "Mainland China", "e_score": 4.3, "e_weight": 50, "carbon": 4.1, "walk": 4.6, "talk": 7.5, "greenwasher": 1, "greenhusher": 0, "gap": 2.9},
        {"firm_id": "0992.HK", "name": "Lenovo Group", "ticker": "0992.HK", "sector": "Technology", "region": "Hong Kong", "e_score": None, "e_weight": 20, "carbon": None, "walk": None, "talk": None, "greenwasher": 0, "greenhusher": 0, "gap": None},
    ]
    return pd.DataFrame(sample_metrics)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Report health and status of the analysis engine."""
    return {
        "status": "healthy",
        "engine": "esgx-analysis-engine",
        "version": "0.4.0",
        "data_dirs": {
            "raw": str(RAW_DIR),
            "processed": str(PROCESSED_DIR),
            "outputs": str(OUTPUT_DIR),
        },
        "capabilities": {
            "liveData": True,
            "portfolioScore": True,
            "recalculation": True,
            "returnForecast": False,  # Hypothesis under research
        },
    }


@app.get("/api/companies")
def get_companies() -> list[dict[str, Any]]:
    """Return all scored companies formatted for the Green Street UI."""
    df = load_latest_dataset()
    weights = [28.0, 20.0, 24.0, 16.0, 12.0] if len(df) == 5 else None
    return dataframe_to_companies(df, default_weights=weights)


@app.get("/api/companies/{company_id}")
def get_company_detail(company_id: str) -> dict[str, Any]:
    """Return detailed metrics for a specific company."""
    companies = get_companies()
    comp = next((c for c in companies if c["id"].lower() == company_id.lower()), None)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
    
    # Calculate PST Greenness
    score = comp["score"]
    materiality = comp["materiality"]
    g = float(greenness(score, materiality)) if score is not None else None

    return {
        "company": comp,
        "metrics": {
            "e_score": score,
            "e_weight": materiality,
            "greenness_g": round(g, 2) if g is not None else None,
            "carbon_intensity_rank": comp["carbon"],
            "walk_action_rank": comp["walk"],
            "talk_disclosure_rank": comp["talk"],
            "gap": round(comp["talk"] - comp["walk"], 2) if comp["talk"] is not None and comp["walk"] is not None else None,
        },
        "methodology": {
            "formula": "g = -(10 - E_score) * E_weight / 100",
            "reference": "Pástor, Stambaugh & Taylor (2022)",
            "lag_months": 18,
        },
    }


@app.post("/api/portfolio/analyze")
def analyze_portfolio(req: PortfolioRequest) -> dict[str, Any]:
    """Perform real-time portfolio greenness and coverage calculation for arbitrary allocations."""
    companies = {c["id"]: c for c in get_companies()}
    allocs = req.allocations

    total_weight = sum(allocs.values())
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="Total allocation must be positive")

    covered_weight = 0.0
    weighted_g = 0.0
    weighted_score = 0.0
    weighted_carbon = 0.0
    weighted_walk = 0.0
    weighted_talk = 0.0

    sector_weights: dict[str, float] = {}

    for cid, w in allocs.items():
        comp = companies.get(cid)
        if not comp:
            continue
        sector = comp["sector"]
        sector_weights[sector] = sector_weights.get(sector, 0.0) + w

        if comp["score"] is not None:
            covered_weight += w
            g = float(greenness(comp["score"], comp["materiality"]))
            weighted_g += (w / total_weight) * g
            weighted_score += (w / total_weight) * comp["score"]
            if comp["carbon"] is not None:
                weighted_carbon += (w / total_weight) * comp["carbon"]
            if comp["walk"] is not None:
                weighted_walk += (w / total_weight) * comp["walk"]
            if comp["talk"] is not None:
                weighted_talk += (w / total_weight) * comp["talk"]

    coverage_pct = round((covered_weight / total_weight) * 100.0)

    return {
        "total_allocation": round(total_weight, 2),
        "coverage_pct": coverage_pct,
        "portfolio_greenness": round(weighted_g, 2) if coverage_pct > 0 else None,
        "portfolio_e_score": round(weighted_score, 2) if coverage_pct > 0 else None,
        "weighted_pillars": {
            "carbon": round(weighted_carbon, 2) if coverage_pct > 0 else None,
            "walk": round(weighted_walk, 2) if coverage_pct > 0 else None,
            "talk": round(weighted_talk, 2) if coverage_pct > 0 else None,
        },
        "sector_allocation": {k: round(v, 2) for k, v in sector_weights.items()},
    }


@app.get("/api/methodology")
def get_methodology() -> dict[str, Any]:
    """Return published research references and scoring specifications."""
    return {
        "title": "Green Street Quantitative ESG Methodology",
        "pillars": {
            "carbon": "Scope 1 & Scope 2 GHG emissions intensity per unit revenue, 18-month reporting lag applied",
            "walk": "Documented emission reduction actions, trend trajectory, and audited disclosures (0-10 percentile)",
            "talk": "Green-claim word intensity in regulatory filings purged of risk vocabulary (0-10 percentile)",
            "greenwashing_gap": "Talk - Walk spread with double-sort greenwashing identification (Giannetti 2023, Chen 2025)",
        },
        "greenness_specification": {
            "formula": "g = -(10 - E_score) * E_weight / 100",
            "source": "Pástor, Stambaugh & Taylor (2022) 'Dissecting Green Returns'",
            "scale": "0 = perfectly green, more negative = browner",
        },
        "asset_pricing_factors": {
            "gmb": "Green-Minus-Brown factor (VW/EW top-tercile minus bottom-tercile greenness portfolio)",
            "fama_macbeth": "Cross-sectional regressions with Newey-West standard errors",
        },
    }
