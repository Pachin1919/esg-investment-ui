"""Canonical tables of the data model.

Every ingest / measure function returns a pandas DataFrame with exactly these
columns (extra columns are allowed, missing ones are not). `validate` is cheap
and is called at module boundaries so mistakes surface early.

Conventions
-----------
* `firm_id`  : yfinance-style ticker (BRK-B, not BRK.B). Stable key across tables.
* `month`    : pandas Period('M'). Returns are for that calendar month.
* `year`     : int fiscal/reporting year.
* Returns are simple, decimal (0.01 = 1%). Factor files from Ken French are converted from %.
* Emissions in metric tons CO2e. Revenue in USD millions. Intensity = tCO2e / USD million.
"""

from __future__ import annotations

import pandas as pd

TABLES: dict[str, list[str]] = {
    # who is in the universe
    "firms": ["firm_id", "name", "sector", "industry", "cik", "country"],
    # monthly market data
    "prices_monthly": ["firm_id", "month", "ret", "mktcap"],
    # Ken French factors, decimal
    "factors_monthly": ["month", "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"],
    # annual fundamentals (SEC XBRL)
    "fundamentals": ["firm_id", "year", "revenue", "book_equity"],
    # annual emissions per firm and source
    "emissions": ["firm_id", "year", "scope1", "scope2", "scope3", "source", "matched"],
    # ESG-style scores from any provider (MSCI-like structure)
    "esg_scores": ["firm_id", "year", "provider", "e_score", "e_weight"],
    # firm x month exposure vector (layer A output)
    "exposure": ["firm_id", "month", "g", "g_across", "g_within", "carbon_intensity"],
    # shock catalogue (layer B input)
    "events": ["event_id", "date", "event_type", "jurisdiction", "description"],
}


def validate(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Raise if `df` lacks required columns for `table`; return df unchanged."""
    required = TABLES[table]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"table '{table}' missing columns {missing}; has {list(df.columns)}")
    return df


def to_month(s: pd.Series) -> pd.Series:
    """Coerce datetimes / strings to Period('M')."""
    if isinstance(s.dtype, pd.PeriodDtype):
        return s
    return pd.to_datetime(s).dt.to_period("M")
