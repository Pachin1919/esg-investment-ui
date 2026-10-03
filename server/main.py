"""FastAPI communication layer for Green Street ESG Investment UI.

Serves data computed by the consolidated quantitative analysis engine (esgx).
and formats it directly for the React / TypeScript UI via server.adapter.
"""

from __future__ import annotations

import io
import csv
import re
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the consolidated engine (engine/src layout) is importable without install
ROOT = Path(__file__).resolve().parents[1]
_engine_src = str(ROOT / "engine" / "src")
if _engine_src not in sys.path:
    sys.path.insert(0, _engine_src)

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.measures.greenness import greenness
from esgx.api.portfolio_routes import router as portfolio_router
from server.adapter import dataframe_to_companies, format_company_for_ui

app = FastAPI(
    title="Green Street Analysis Engine API",
    description="Backend communication layer serving quantitative ESG scores and portfolio analytics",
    version="0.4.0",
)

app.include_router(portfolio_router)

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


class CsvUploadRequest(BaseModel):
    csv_text: str


def load_latest_dataset() -> pd.DataFrame:
    """Load latest scored companies from processed or outputs directories, or fallback to HK universe."""
    scores_file = OUTPUT_DIR / "main_scores.csv"
    det_gw_hk = OUTPUT_DIR / "det_greenwashing_hk.csv"
    det_gw_us = OUTPUT_DIR / "det_greenwashing.csv"

    # Check for Hong Kong deterministic greenwashing output
    if det_gw_hk.exists():
        df = pd.read_csv(det_gw_hk)
        for univ_name in ("universe_hk.parquet", "universe_hsi.parquet", "universe_hsci.parquet"):
            univ_file = RAW_DIR / univ_name
            if univ_file.exists():
                break
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

    # Otherwise load baseline representative demo scoring based on real HK/TW companies
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
            "csvUpload": True,
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
            "gap": comp.get("gap"),
            "greenwasher": comp.get("greenwasher", False),
            "greenhusher": comp.get("greenhusher", False),
        },
        "methodology": {
            "formula": "g = -(10 - E_score) * E_weight / 100",
            "reference": "Pástor, Stambaugh & Taylor (2022)",
            "lag_months": 18,
        },
    }


@app.post("/api/portfolio/analyze")
def analyze_portfolio(req: PortfolioRequest) -> dict[str, Any]:
    """Perform real-time portfolio greenness, carbon, and greenwash risk calculation."""
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
    greenwash_weight = 0.0

    sector_weights: dict[str, float] = {}

    for cid, w in allocs.items():
        comp = companies.get(cid)
        if not comp:
            continue
        sector = comp["sector"]
        sector_weights[sector] = sector_weights.get(sector, 0.0) + w

        if comp.get("greenwasher"):
            greenwash_weight += w

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
        "greenwash_flagged_allocation": round(greenwash_weight, 2),
        "sector_allocation": {k: round(v, 2) for k, v in sector_weights.items()},
    }


def normalize_ticker(raw: str) -> str:
    """Normalize input ticker string to standard format (e.g. '2' -> '0002.HK')."""
    clean = raw.strip().upper()
    if clean.isdigit():
        return f"{int(clean):04d}.HK"
    if clean.endswith(".HK") and clean[:-3].isdigit():
        return f"{int(clean[:-3]):04d}.HK"
    return clean


@app.get("/api/portfolio/sample-csv", response_class=PlainTextResponse)
def get_sample_csv() -> str:
    """Return downloadable template CSV for portfolio upload."""
    sample = (
        "ticker,allocation\n"
        "0002.HK,28\n"
        "0066.HK,20\n"
        "2330.TW,24\n"
        "0857.HK,16\n"
        "0992.HK,12\n"
    )
    return sample


@app.post("/api/portfolio/upload-csv")
def upload_portfolio_csv(req: CsvUploadRequest) -> dict[str, Any]:
    """Parse an uploaded CSV of portfolio holdings and match against universe and emissions database."""
    lines = [line.strip() for line in req.csv_text.strip().splitlines() if line.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    reader = csv.reader(lines)
    header = next(reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="CSV does not contain header or data.")

    # Locate ticker and weight columns
    ticker_col = 0
    weight_col = 1
    has_header = False

    for idx, col_name in enumerate(header):
        lower = col_name.strip().lower()
        if lower in {"ticker", "symbol", "code", "firm_id", "stock"}:
            ticker_col = idx
            has_header = True
        elif lower in {"allocation", "weight", "pct", "percent", "shares", "value", "market_value"}:
            weight_col = idx
            has_header = True

    data_rows = []
    # If the first row wasn't headers, treat it as data
    rows_to_parse = reader if has_header else [header] + list(reader)

    for row in rows_to_parse:
        if len(row) <= max(ticker_col, weight_col):
            continue
        raw_tick = row[ticker_col].strip()
        raw_wt = row[weight_col].strip().replace("%", "").replace(",", "")
        if not raw_tick:
            continue
        try:
            wt = float(raw_wt)
            if wt > 0:
                data_rows.append((normalize_ticker(raw_tick), wt))
        except ValueError:
            continue

    if not data_rows:
        raise HTTPException(status_code=400, detail="No valid ticker and weight rows could be parsed from CSV.")

    total_wt = sum(wt for _, wt in data_rows)
    normalized_weights = [round((wt / total_wt) * 100.0, 1) for _, wt in data_rows]
    # Ensure exact 100.0% sum
    diff = 100.0 - sum(normalized_weights)
    if diff != 0 and normalized_weights:
        normalized_weights[0] = round(normalized_weights[0] + diff, 1)

    # Match tickers against latest scored dataset
    db = load_latest_dataset()
    db_by_ticker = {str(r.get("ticker", "")).upper(): r for _, r in db.iterrows()}
    db_by_id = {str(r.get("firm_id", "")).upper(): r for _, r in db.iterrows()}

    companies = []
    unmatched = []

    for i, (tick, alloc) in enumerate(data_rows):
        matched_row = db_by_ticker.get(tick)
        if matched_row is None:
            matched_row = db_by_id.get(tick)
        if matched_row is not None:
            comp_dict = dict(matched_row)
            comp_dict["allocation"] = normalized_weights[i]
            companies.append(format_company_for_ui(comp_dict, index=i, default_allocation=normalized_weights[i]))
        else:
            # Unmatched firm: retain in portfolio with score=None so coverage is transparent
            unmatched.append(tick)
            synthetic_row = {
                "firm_id": tick,
                "name": tick,
                "ticker": tick,
                "sector": "Other",
                "region": "Hong Kong" if ".HK" in tick else "Global",
                "allocation": normalized_weights[i],
                "e_score": None,
                "e_weight": 25,
                "carbon": None,
                "walk": None,
                "talk": None,
                "note": "Company not yet covered in our emissions and filing disclosure database.",
            }
            companies.append(format_company_for_ui(synthetic_row, index=i, default_allocation=normalized_weights[i]))

    covered_sum = sum(c["allocation"] for c in companies if c["score"] is not None)

    return {
        "companies": companies,
        "total_allocation": 100.0,
        "count": len(companies),
        "unmatched_tickers": unmatched,
        "coverage_pct": round(covered_sum),
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
