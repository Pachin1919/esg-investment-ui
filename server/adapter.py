"""Adapter layer: transforms analysis engine outputs into the Green Street UI view models.

Maintains strict separation between the quantitative analysis engine and the UI.
Ensures missing scores are preserved as None/null (never zero).
"""

from __future__ import annotations

import re
import math
from typing import Any
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


def number(value: Any) -> float | None:
    """Finite scalar numbers only; pandas missing scalars never enter truth tests."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def text(value: Any, fallback: str) -> str:
    if value is None or value is pd.NA or value is pd.NaT:
        return fallback
    if not isinstance(value, str) and number(value) is None:
        return fallback
    return str(value).strip() or fallback


def flag(value: Any) -> bool | None:
    result = number(value)
    return bool(result) if result in (0, 1) else None


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
    greenwasher = flag(row.get("greenwasher"))
    greenhusher = flag(row.get("greenhusher"))
    gap = number(row.get("gap"))
    score = number(row.get("e_score"))

    if score is None:
        return "Environmental score unavailable in this dataset. Missing data does not indicate low risk."
    if greenwasher is None or greenhusher is None:
        return "Environmental score available; insufficient Talk and Walk evidence for a greenwashing assessment."
    if greenwasher:
        return "Disclosed ambitions outpace documented actions (top-quintile talk vs. bottom-tercile walk within industry)."
    if greenhusher:
        return "Significant documented operational improvements accompany relatively modest public sustainability disclosure."
    if gap is not None and not pd.isna(gap):
        if gap > 3.0:
            return "A notable Talk - Walk gap is observed; review underlying verification and capex commitments."
        elif gap < -2.0:
            return "Documented emissions reductions and targets are progressing ahead of general industry communication."
    return "Scores reflect the dataset's emissions and disclosure measures; assessment flags are research indicators, not audit conclusions."


def format_company_for_ui(
    row: pd.Series | dict[str, Any],
    index: int = 0,
    default_allocation: float = 0.0,
) -> dict[str, Any]:
    """Convert an analyzed firm record into the TypeScript Company interface."""
    firm_id = text(row.get("firm_id"), f"firm_{index}")
    name = text(row.get("name"), firm_id)
    ticker = text(row.get("ticker"), firm_id)
    sector = text(row.get("sector"), "General")
    region = text(row.get("region"), text(row.get("country"), "Taiwan" if ticker.upper().endswith((".TW", ".TWO")) else "Hong Kong"))

    def to_float_or_none(val: Any) -> float | None:
        f = number(val)
        return round(f, 1) if f is not None else None

    score = to_float_or_none(row.get("e_score"))
    materiality_raw = row.get("e_weight")
    materiality = round(number(materiality_raw)) if number(materiality_raw) is not None else 30
    carbon = to_float_or_none(row.get("carbon"))
    if carbon is None:
        carbon = to_float_or_none(row.get("walk_intensity_level"))
    walk = to_float_or_none(row.get("walk"))
    talk = to_float_or_none(row.get("talk"))

    color = text(row.get("color"), COMPANY_PALETTE[index % len(COMPANY_PALETTE)])
    initials = extract_initials(name, ticker)
    note = text(row.get("note"), build_company_note(row))

    gap = to_float_or_none(row.get("gap"))
    if gap is None and talk is not None and walk is not None:
        gap = round(talk - walk, 1)
    assessed = flag(row.get("greenwasher")) is not None and flag(row.get("greenhusher")) is not None and talk is not None and walk is not None

    return {
        "id": firm_id.lower().replace(".", "-"),
        "name": name,
        "ticker": ticker,
        "sector": sector,
        "region": region,
        "listing_market": text(row.get("exchange"), "HKEX" if ticker.upper().endswith(".HK") else "TPEx" if ticker.upper().endswith(".TWO") else "TWSE" if ticker.upper().endswith(".TW") else "Unknown"),
        "listing_region": "hk" if ticker.upper().endswith(".HK") else "tw" if ticker.upper().endswith((".TW", ".TWO")) else None,
        "listing_currency": "HKD" if ticker.upper().endswith(".HK") else "TWD" if ticker.upper().endswith((".TW", ".TWO")) else None,
        "model_proxy": "Asia Pacific ex Japan regional factor proxy (USD)" if ticker.upper().endswith(".HK") else "Emerging regional factor proxy (USD)" if ticker.upper().endswith((".TW", ".TWO")) else None,
        "domicile": text(row.get("domicile"), "") or None,
        "allocation": number(row.get("allocation")) if number(row.get("allocation")) is not None else default_allocation,
        "score": score,
        "materiality": materiality,
        "carbon": carbon,
        "walk": walk,
        "talk": talk,
        "gap": gap,
        "greenwasher": flag(row.get("greenwasher")) if assessed else None,
        "greenhusher": flag(row.get("greenhusher")) if assessed else None,
        "assessment_status": "assessed" if assessed else "insufficient_data",
        "color": color,
        "initials": initials,
        "note": note,
    }


def dataframe_to_companies(df: pd.DataFrame, default_weights: list[float] | None = None) -> list[dict[str, Any]]:
    """Convert an entire scored DataFrame to a list of Company view models."""
    companies = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        alloc = default_weights[i] if default_weights and i < len(default_weights) else (round(100.0 / n, 2) if n else 0)
        companies.append(format_company_for_ui(row, index=i, default_allocation=alloc))
    
    # Ensure total default allocation sums to exactly 100%
    if companies and (default_weights is None or sum(default_weights) != 100):
        tot = sum(c["allocation"] for c in companies)
        if tot != 100 and tot > 0:
            diff = 100 - tot
            companies[0]["allocation"] = round(companies[0]["allocation"] + diff, 2)
    return companies
