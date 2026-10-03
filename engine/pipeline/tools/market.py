"""Market data tools: monthly prices (yfinance) and Ken French factors."""

from __future__ import annotations

import pandas as pd

from esgx.ingest.factors import load_factors as _factors
from esgx.ingest.prices import load_prices as _prices
from pipeline.tools.base import tool


@tool(kind="api", cost="network")
def yf_monthly_prices(tickers: list[str], refresh: bool = False) -> pd.DataFrame:
    """Monthly prices, returns and market caps for tickers via yfinance (cached parquet)."""
    return _prices(tickers, refresh=refresh)


@tool(kind="api", cost="network")
def french_factors(region: str = "asia_pacific_ex_japan", refresh: bool = False) -> pd.DataFrame:
    """Fama-French 5 factors + momentum, monthly, from the Ken French data library (cached)."""
    return _factors(refresh=refresh, region=region)
