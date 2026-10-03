"""Monthly returns and market cap from yfinance.

Market cap uses the shares-outstanding history endpoint where available, else
the latest share count (flat). Both are approximations; document in results.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from esgx.config import RAW_DIR, START_YEAR
from esgx.schema import validate


def _download_close(tickers: list[str], start: str) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        px = yf.download(
            tickers, start=start, interval="1mo", auto_adjust=True, progress=False, threads=True
        )
    close = px["Close"] if isinstance(px.columns, pd.MultiIndex) else px[["Close"]]
    if not isinstance(px.columns, pd.MultiIndex):
        close.columns = tickers
    close.index = pd.to_datetime(close.index).to_period("M")
    return close


def _shares_history(tickers: list[str]) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for t in tqdm(tickers, desc="shares", leave=False):
        try:
            s = yf.Ticker(t).get_shares_full(start=f"{START_YEAR}-01-01")
            if s is not None and len(s):
                s = s[~s.index.duplicated(keep="last")]
                s.index = pd.to_datetime(s.index).tz_localize(None).to_period("M")
                out[t] = s.groupby(level=0).last()
        except Exception:  # noqa: BLE001, S112 – yfinance is flaky per ticker; fall back to flat shares
            continue
    return out


def load_prices(tickers: list[str], refresh: bool = False, cache_name: str = "prices_monthly") -> pd.DataFrame:
    """`cache_name` separates markets (e.g. "prices_monthly_hk"). Market cap is in the
    listing currency (USD for S&P 500, HKD for SEHK); it is only used for VW weights."""
    path = RAW_DIR / f"{cache_name}.parquet"
    if path.exists() and not refresh:
        df = pd.read_parquet(path)
        df["month"] = pd.PeriodIndex(df["month"], freq="M")
        return df

    start = f"{START_YEAR - 1}-12-01"
    close = _download_close(tickers, start)
    ret = close.pct_change()

    shares = _shares_history(list(close.columns))
    months = close.index
    mktcap = pd.DataFrame(index=months, columns=close.columns, dtype=float)
    for t in close.columns:
        if t in shares:
            sh = shares[t].reindex(months).ffill().bfill()
        else:
            sh = pd.Series(np.nan, index=months)
        mktcap[t] = close[t] * sh

    long = (
        pd.concat({"ret": ret, "mktcap": mktcap}, axis=1)
        .stack(level=1, future_stack=True)
        .reset_index()
    )
    long.columns = ["month", "firm_id", "ret", "mktcap"]
    long = long.dropna(subset=["ret"])
    long = long[long["month"].dt.year >= START_YEAR].reset_index(drop=True)
    validate(long, "prices_monthly")
    long.assign(month=long["month"].astype(str)).to_parquet(path, index=False)
    return long
