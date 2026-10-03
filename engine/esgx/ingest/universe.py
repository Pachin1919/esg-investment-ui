"""S&P 500 constituents from Wikipedia (free, includes GICS sector and CIK).

Survivorship caveat: this is the *current* list, so backtests over-represent
survivors. Good enough for phase 0; a point-in-time list is a phase 1 item.
"""

from __future__ import annotations

import io

import pandas as pd
import requests

from esgx.config import RAW_DIR
from esgx.schema import validate

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)"}


def _yf_symbol(sym: str) -> str:
    return sym.strip().replace(".", "-")


def load_universe(refresh: bool = False) -> pd.DataFrame:
    path = RAW_DIR / "universe_sp500.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    html = requests.get(WIKI_URL, headers=_HEADERS, timeout=30).text
    tables = pd.read_html(io.StringIO(html))
    t = tables[0]
    cols = {c: str(c).strip() for c in t.columns}
    t = t.rename(columns=cols)
    df = pd.DataFrame(
        {
            "firm_id": t["Symbol"].map(_yf_symbol),
            "name": t["Security"].astype(str),
            "sector": t["GICS Sector"].astype(str),
            "industry": t["GICS Sub-Industry"].astype(str),
            "cik": pd.to_numeric(t["CIK"], errors="coerce").astype("Int64"),
            "country": "US",
        }
    )
    df = df.drop_duplicates("firm_id").reset_index(drop=True)
    validate(df, "firms")
    df.to_parquet(path, index=False)
    return df
