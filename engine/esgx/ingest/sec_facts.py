"""Annual revenue and book equity from the SEC XBRL companyfacts API (free).

Docs: https://www.sec.gov/edgar/sec-api-documentation . Rate limit 10 req/s,
User-Agent required (set ESGX_SEC_USER_AGENT).
"""

from __future__ import annotations

import time

import pandas as pd
import requests
from tqdm import tqdm

from esgx.config import RAW_DIR, SEC_USER_AGENT
from esgx.schema import validate

URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "RevenuesNetOfInterestExpense",
    "TotalRevenuesAndOtherIncome",
]
EQUITY_TAGS = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]


def _tag_series(units: dict) -> pd.Series:
    """FY values from 10-K filings for one tag, keyed by calendar frame year (CY2019) when
    available, else by fiscal year. One value per year (latest filed)."""
    vals = units.get("USD")
    if not vals:
        return pd.Series(dtype=float)
    df = pd.DataFrame(vals)
    if "form" not in df.columns or "fp" not in df.columns:
        return pd.Series(dtype=float)
    df = df[(df["form"] == "10-K") & (df["fp"] == "FY")].copy()
    if df.empty:
        return pd.Series(dtype=float)
    frame = df["frame"].fillna("") if "frame" in df.columns else pd.Series("", index=df.index)
    has_frame = frame.str.match(r"^CY\d{4}$")
    df["year"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df.loc[has_frame, "year"] = frame[has_frame].str[2:].astype(int)
    # rows without a frame: fall back to the fiscal year; frames win on conflict
    df.loc[~has_frame, "year"] = pd.to_numeric(df.loc[~has_frame, "fy"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year"])
    df["has_frame"] = has_frame.astype(int)
    df = df.sort_values(["year", "has_frame", "filed"])
    return df.groupby("year")["val"].last().astype(float)


def _annual_series(facts: dict, tags: list[str]) -> pd.Series:
    """Union of annual values across tags, earlier tags in the list taking priority."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    out = pd.Series(dtype=float)
    for tag in tags:
        s = _tag_series(gaap.get(tag, {}).get("units", {}))
        out = out.combine_first(s) if len(out) else s
    return out.sort_index()


def load_fundamentals(firms: pd.DataFrame, refresh: bool = False) -> pd.DataFrame:
    path = RAW_DIR / "fundamentals.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    sess = requests.Session()
    sess.headers.update({"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    rows = []
    for _, r in tqdm(list(firms.iterrows()), desc="sec facts", leave=False):
        if pd.isna(r["cik"]):
            continue
        try:
            resp = sess.get(URL.format(cik=int(r["cik"])), timeout=30)
            time.sleep(0.11)
            if resp.status_code != 200:
                continue
            facts = resp.json()
        except Exception:  # noqa: BLE001, S112 – skip firms whose companyfacts call fails
            continue
        rev = _annual_series(facts, REVENUE_TAGS) / 1e6
        eq = _annual_series(facts, EQUITY_TAGS) / 1e6
        years = sorted(set(rev.index) | set(eq.index))
        for y in years:
            rows.append(
                {
                    "firm_id": r["firm_id"],
                    "year": int(y),
                    "revenue": float(rev.get(y, float("nan"))),
                    "book_equity": float(eq.get(y, float("nan"))),
                }
            )
    df = pd.DataFrame(rows, columns=["firm_id", "year", "revenue", "book_equity"])
    validate(df, "fundamentals")
    df.to_parquet(path, index=False)
    return df
