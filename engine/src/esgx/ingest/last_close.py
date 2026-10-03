"""Latest unadjusted close per ticker from yfinance, in the listing currency.

Only used to turn recommended capital into share counts (`portfolio.positions`); returns
and market cap keep coming from `ingest.prices`. Cached to data/raw/last_close_<market>.parquet.
"""

from __future__ import annotations

import warnings

import pandas as pd
import yfinance as yf

from esgx.config import RAW_DIR


def load_last_close(tickers: list[str], market: str = "hk", refresh: bool = False) -> pd.DataFrame:
    """firm_id, date, close: the last available daily close of each ticker (missing tickers dropped)."""
    path = RAW_DIR / f"last_close_{market}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        px = yf.download(tickers, period="5d", interval="1d", auto_adjust=False, progress=False, threads=True)
    close = px["Close"] if isinstance(px.columns, pd.MultiIndex) else px[["Close"]].set_axis(tickers, axis=1)
    last = close.ffill().iloc[-1].dropna()
    out = pd.DataFrame({"firm_id": last.index, "date": str(close.index[-1].date()), "close": last.to_numpy(float)})
    out.to_parquet(path, index=False)
    return out
