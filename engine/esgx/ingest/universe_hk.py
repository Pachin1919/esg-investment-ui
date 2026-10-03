"""Hang Seng Index constituents (Hong Kong) as a second universe.

Sources (all free)
* Wikipedia "Hang Seng Index" constituent table: SEHK stock code, name, HSI sub-index.
* HKEXnews active-stock map: stock code -> internal `stockId` used by the HKEXnews
  title-search API (https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json).
* yfinance `.info`: sector / industry (GICS-like), domicile country.

`firm_id` is the yfinance symbol, e.g. "0005.HK". `cik` is NA (no SEC filer id);
`stock_code` (int) and `hkex_sid` (int) are the HKEX keys.

Survivorship caveat as for the S&P 500 list: this is the *current* index.
"""

from __future__ import annotations

import io
import re

import pandas as pd
import requests
from tqdm import tqdm

from esgx.config import RAW_DIR
from esgx.schema import validate

WIKI_URL = "https://en.wikipedia.org/wiki/Hang_Seng_Index"
STOCK_MAP_URL = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"
_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)"}


def code_from_ticker(s: str) -> int | None:
    """'SEHK: 5' / 'SEHK:0005' / '5' -> 5."""
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else None


def yf_symbol(code: int) -> str:
    """5 -> '0005.HK' (yfinance uses 4-digit zero-padded codes)."""
    return f"{int(code):04d}.HK"


def load_hkex_stock_map(refresh: bool = False) -> pd.DataFrame:
    """stock_code -> hkex_sid, hkex_name for all active SEHK securities."""
    path = RAW_DIR / "hkex_stock_map.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    rows = requests.get(STOCK_MAP_URL, headers=_HEADERS, timeout=60).json()
    df = pd.DataFrame({"stock_code": [int(r["c"]) for r in rows], "hkex_sid": [int(r["i"]) for r in rows], "hkex_name": [r["n"] for r in rows]})
    df.to_parquet(path, index=False)
    return df


def _wiki_constituents() -> pd.DataFrame:
    html = requests.get(WIKI_URL, headers=_HEADERS, timeout=30).text
    tables = pd.read_html(io.StringIO(html))
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any("Ticker" in c or "Stock code" in c for c in cols) and len(t) > 40:
            t.columns = cols
            tick = next(c for c in cols if "Ticker" in c or "Stock code" in c)
            name = next(c for c in cols if "Name" in c or "Company" in c)
            sub = next((c for c in cols if "index" in c.lower() or "Industry" in c), None)
            out = pd.DataFrame({"stock_code": t[tick].map(code_from_ticker), "name": t[name].astype(str)})
            out["sub_index"] = t[sub].astype(str) if sub else ""
            return out.dropna(subset=["stock_code"]).astype({"stock_code": int})
    raise RuntimeError("HSI constituent table not found on Wikipedia")


def _yf_info(symbols: list[str]) -> pd.DataFrame:
    import yfinance as yf

    rows = []
    for s in tqdm(symbols, desc="yf info", leave=False):
        try:
            info = yf.Ticker(s).info or {}
        except Exception:  # noqa: BLE001 – yfinance is flaky per ticker
            info = {}
        rows.append({"firm_id": s, "sector": info.get("sector"), "industry": info.get("industry"), "domicile": info.get("country"), "currency": info.get("currency")})
    return pd.DataFrame(rows)


def load_universe_hk(refresh: bool = False) -> pd.DataFrame:
    path = RAW_DIR / "universe_hsi.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    wiki = _wiki_constituents()
    wiki["firm_id"] = wiki["stock_code"].map(yf_symbol)
    info = _yf_info(wiki["firm_id"].tolist())
    smap = load_hkex_stock_map(refresh=refresh)
    df = wiki.merge(info, on="firm_id", how="left").merge(smap, on="stock_code", how="left")
    df["sector"] = df["sector"].fillna(df["sub_index"]).astype(str)
    df["industry"] = df["industry"].fillna(df["sub_index"]).astype(str)
    df["cik"] = pd.array([pd.NA] * len(df), dtype="Int64")
    df["country"] = "HK"  # listing market; `domicile` keeps the yfinance country
    df["hkex_sid"] = df["hkex_sid"].astype("Int64")
    df = df[["firm_id", "name", "sector", "industry", "cik", "country", "stock_code", "hkex_sid", "hkex_name", "sub_index", "domicile", "currency"]]
    df = df.drop_duplicates("firm_id").reset_index(drop=True)
    validate(df, "firms")
    df.to_parquet(path, index=False)
    return df
