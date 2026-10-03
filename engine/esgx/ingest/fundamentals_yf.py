"""Annual revenue and book equity from yfinance statements (markets without an XBRL API).

yfinance exposes ~4-5 fiscal years of income statement / balance sheet per ticker.
Values are converted to USD millions with a fixed rate table so the `fundamentals`
schema (USD millions) holds across markets. HKD is pegged (7.75-7.85 per USD), so the
fixed 7.8 is accurate to within 1%; CNY uses a rough average and is flagged in `fx_note`.
"""

from __future__ import annotations

import warnings

import pandas as pd
from tqdm import tqdm

from esgx.config import RAW_DIR
from esgx.schema import validate

USD_PER_UNIT = {"USD": 1.0, "HKD": 1 / 7.8, "CNY": 1 / 7.2, "RMB": 1 / 7.2, "EUR": 1.1, "GBP": 1.27}
REVENUE_ROWS = ["Total Revenue", "Operating Revenue"]
EQUITY_ROWS = ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"]


def _first_row(df: pd.DataFrame | None, names: list[str]) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    for n in names:
        if n in df.index:
            return df.loc[n]
    return pd.Series(dtype=float)


def load_fundamentals_yf(firms: pd.DataFrame, refresh: bool = False, cache_name: str = "fundamentals_yf") -> pd.DataFrame:
    import yfinance as yf

    path = RAW_DIR / f"{cache_name}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    rows = []
    for firm_id in tqdm(firms["firm_id"].tolist(), desc="yf fundamentals", leave=False):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = yf.Ticker(firm_id)
                inc, bal = t.financials, t.balance_sheet
                ccy = (t.info or {}).get("financialCurrency") or (t.info or {}).get("currency") or "USD"
        except Exception:  # noqa: BLE001, S112 – yfinance is flaky per ticker; skip it
            continue
        fx = USD_PER_UNIT.get(ccy)
        rev, eq = _first_row(inc, REVENUE_ROWS), _first_row(bal, EQUITY_ROWS)
        for col in set(rev.index) | set(eq.index):
            year = pd.Timestamp(col).year
            r, e = rev.get(col), eq.get(col)
            rows.append({
                "firm_id": firm_id, "year": year,
                "revenue": float(r) * fx / 1e6 if pd.notna(r) and fx else float("nan"),
                "book_equity": float(e) * fx / 1e6 if pd.notna(e) and fx else float("nan"),
                "currency": ccy, "fx_note": "fixed peg" if ccy == "HKD" else ("approx avg rate" if ccy in ("CNY", "RMB") else "fixed"),
            })
    df = pd.DataFrame(rows, columns=["firm_id", "year", "revenue", "book_equity", "currency", "fx_note"])
    df = df.sort_values(["firm_id", "year"]).drop_duplicates(["firm_id", "year"], keep="last").reset_index(drop=True)
    validate(df, "fundamentals")
    df.to_parquet(path, index=False)
    return df
