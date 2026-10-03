"""Adapter layer: transforms analysis engine outputs into the Green Street UI view models.

Maintains strict separation between the quantitative analysis engine and the UI.
Ensures missing scores are preserved as None/null (never zero).
"""

from __future__ import annotations

import re
from typing import Any
import numpy as np
import pandas as pd

# Palette of distinct, accessible colors for companies
COMPANY_PALETTE = [
    "#629dcc",  # Blue
    "#93c9bf",  # Sage
    "#a5b8dc",  # Periwinkle
    "#d7bd89",  # Ochre / Gold
    "#8eb897",  # Soft Green
    "#b89ec9",  # Lavender
    "#cca58a",  # Warm Sand
    "#6ba292",  # Sea Green
    "#e29578",  # Terracotta
    "#83c5be",  # Duck Egg
]


def extract_initials(name: str, ticker: str) -> str:
    """Extract 2-character uppercase initials for company avatar."""
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", name).strip()
    words = [w for w in cleaned.split() if w.upper() not in {"CORP", "INC", "LTD", "LIMITED", "HOLDINGS", "GROUP", "CO"}]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    elif len(words) == 1 and len(words[0]) >= 2:
        return words[0][:2].upper()
    clean_ticker = re.sub(r"[^A-Za-z0-9]+", "", ticker)
    return clean_ticker[:2].upper() if clean_ticker else "GS"


def build_company_note(row: pd.Series | dict[str, Any]) -> str:
    """Generate a neutral, research-backed explanatory note from score flags."""
    greenwasher = row.get("greenwasher") == 1
    greenhusher = row.get("greenhusher") == 1
    gap = row.get("gap")
    score = row.get("e_score")

    if score is None or pd.isna(score):
        return "No complete emissions or environmental filing disclosure is currently available for this company."
    if greenwasher:
        return "Disclosed ambitions outpace documented actions (top-quintile talk vs. bottom-tercile walk within industry)."
    if greenhusher:
        return "Significant documented operational improvements accompany relatively modest public sustainability disclosure."
    if gap is not None and not pd.isna(gap):
        if gap > 3.0:
            return "A notable Talk - Walk gap is observed; review underlying verification and capex commitments."
        elif gap < -2.0:
            return "Documented emissions reductions and targets are progressing ahead of general industry communication."
    return "Scores reflect audited Scope 1/2 emissions intensity and disclosure metrics from regulatory filings."


def format_company_for_ui(
    row: pd.Series | dict[str, Any],
    index: int = 0,
    default_allocation: float = 0.0,
) -> dict[str, Any]:
    """Convert an analyzed firm record into the TypeScript Company interface."""
    firm_id = str(row.get("firm_id", f"firm_{index}"))
    name = str(row.get("name") or firm_id)
    ticker = str(row.get("ticker") or firm_id)
    sector = str(row.get("sector") or "General")
    region = str(row.get("country") or row.get("region") or ("Hong Kong" if ".HK" in ticker.upper() or firm_id.isdigit() else "US"))

    def to_float_or_none(val: Any) -> float | None:
        if val is None or pd.isna(val):
            return None
        try:
            f = float(val)
            return round(f, 1) if not np.isnan(f) else None
        except (ValueError, TypeError):
            return None

    score = to_float_or_none(row.get("e_score"))
    materiality_raw = row.get("e_weight")
    materiality = round(float(materiality_raw)) if materiality_raw is not None and not pd.isna(materiality_raw) else 30
    carbon = to_float_or_none(row.get("carbon") or row.get("walk_intensity_level"))
    walk = to_float_or_none(row.get("walk"))
    talk = to_float_or_none(row.get("talk"))

    color = str(row.get("color") or COMPANY_PALETTE[index % len(COMPANY_PALETTE)])
    initials = extract_initials(name, ticker)
    note = str(row.get("note") or build_company_note(row))

    gap = to_float_or_none(row.get("gap"))
    if gap is None and talk is not None and walk is not None:
        gap = round(talk - walk, 1)

    return {
        "id": firm_id.lower().replace(".", "-"),
        "name": name,
        "ticker": ticker,
        "sector": sector,
        "region": region,
        "allocation": float(row.get("allocation", default_allocation)),
        "score": score,
        "materiality": materiality,
        "carbon": carbon,
        "walk": walk,
        "talk": talk,
        "gap": gap,
        "greenwasher": bool(row.get("greenwasher") == 1),
        "greenhusher": bool(row.get("greenhusher") == 1),
        "color": color,
        "initials": initials,
        "note": note,
    }


def dataframe_to_companies(df: pd.DataFrame, default_weights: list[float] | None = None) -> list[dict[str, Any]]:
    """Convert an entire scored DataFrame to a list of Company view models."""
    companies = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        alloc = default_weights[i] if default_weights and i < len(default_weights) else (round(100.0 / n) if n else 0)
        companies.append(format_company_for_ui(row, index=i, default_allocation=alloc))
    
    # Ensure total default allocation sums to exactly 100%
    if companies and (default_weights is None or sum(default_weights) != 100):
        tot = sum(c["allocation"] for c in companies)
        if tot != 100 and tot > 0:
            diff = 100 - tot
            companies[0]["allocation"] += diff
    return companies
