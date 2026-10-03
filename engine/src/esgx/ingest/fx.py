"""Monthly exchange rates for restating a market's returns in the investor's base currency.

The base currency is HKD (the product serves Hong Kong investors). One row per month and
pair: `rate` is base currency per unit of the quoted currency at month end, e.g. pair
"TWDHKD" = HKD per 1 TWD. Source: yfinance cross rates ("TWDHKD=X"), cached to parquet.
"""

from __future__ import annotations

import warnings

import pandas as pd
import yfinance as yf

from esgx.config import RAW_DIR, START_YEAR
from esgx.schema import validate

BASE_CURRENCY = "HKD"
MARKET_CURRENCY = {"hk": "HKD", "tw": "TWD"}


def pair_for(market: str) -> str | None:
    """FX pair that restates `market` in the base currency; None when it already is."""
    ccy = MARKET_CURRENCY[market]
    return None if ccy == BASE_CURRENCY else f"{ccy}{BASE_CURRENCY}"


def load_fx(pairs: list[str] | None = None, refresh: bool = False) -> pd.DataFrame:
    """Month-end rates for `pairs` (default: every non-base market currency)."""
    path = RAW_DIR / "fx_monthly.parquet"
    if path.exists() and not refresh:
        df = pd.read_parquet(path)
        df["month"] = pd.PeriodIndex(df["month"], freq="M")
        return df
    pairs = pairs or sorted({p for m in MARKET_CURRENCY if (p := pair_for(m))})
    frames = []
    for pair in pairs:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            px = yf.download(f"{pair}=X", start=f"{START_YEAR - 1}-12-01", interval="1mo",
                             auto_adjust=True, progress=False)
        close = px["Close"].squeeze("columns").dropna()
        frames.append(pd.DataFrame({"month": pd.to_datetime(close.index).to_period("M"),
                                    "pair": pair, "rate": close.to_numpy(dtype=float)}))
    df = pd.concat(frames, ignore_index=True).drop_duplicates(["month", "pair"], keep="last")
    validate(df, "fx_monthly")
    df.assign(month=df["month"].astype(str)).to_parquet(path, index=False)
    return df
