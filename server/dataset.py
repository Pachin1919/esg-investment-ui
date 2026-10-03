"""Scored-company loader for the UI: one row per firm (latest scored year) with E_score/E_weight
from the greenness table, talk/walk and flags from the greenwashing table where the firm has
them, and name/sector/region from the market's universe files."""

from __future__ import annotations

import pandas as pd
from esgx.config import OUTPUT_DIR, RAW_DIR

UNIVERSE_FILES = {"hk": ("universe_hk.parquet", "universe_hsi.parquet", "universe_hsci.parquet"),
                  "tw": ("universe_twse.parquet",)}
MARKET_REGION = {"hk": "Hong Kong", "tw": "Taiwan"}
# HKEX-listed firms are labelled by domicile when it is inside scope, else by listing venue.
SCOPE_DOMICILES = {"Hong Kong", "China", "Macau", "Taiwan"}


def _universe(market: str) -> pd.DataFrame:
    """All universe files of the market stacked, first occurrence of a firm wins."""
    frames = [pd.read_parquet(RAW_DIR / n) for n in UNIVERSE_FILES[market] if (RAW_DIR / n).exists()]
    if not frames:
        return pd.DataFrame(columns=["firm_id", "name"])
    univ = pd.concat(frames, ignore_index=True).drop_duplicates("firm_id")
    return univ[["firm_id", "name"] + [c for c in ("ticker", "domicile", "sector") if c in univ.columns]]


def _region(df: pd.DataFrame, market: str) -> pd.Series:
    default = MARKET_REGION[market]
    if "domicile" not in df.columns:
        return pd.Series(default, index=df.index)
    return df["domicile"].where(df["domicile"].isin(SCOPE_DOMICILES), default)


def load_market(market: str) -> pd.DataFrame | None:
    """Latest scored year per firm for one market, or None when the market has no output yet.

    A firm is listed as soon as it has greenness (E-score); talk, walk, gap and the flags stay
    missing until the greenwashing table covers it, so every firm the optimizer can recommend
    on greenness is also searchable."""
    det, green = OUTPUT_DIR / f"det_greenwashing_{market}.csv", OUTPUT_DIR / f"det_greenness_{market}.csv"
    if not det.exists() and not green.exists():
        return None
    df = (pd.read_csv(det).sort_values("year").drop_duplicates("firm_id", keep="last") if det.exists()
          else pd.DataFrame(columns=["firm_id", "year"]))
    if green.exists():
        g = pd.read_csv(green)[["firm_id", "year", "e_score", "e_weight"]].drop_duplicates(["firm_id", "year"])
        df = df.merge(g, on=["firm_id", "year"], how="left")
        only_green = g.sort_values("year").drop_duplicates("firm_id", keep="last")
        only_green = only_green[~only_green["firm_id"].isin(df["firm_id"])]
        df = pd.concat([df, only_green], ignore_index=True) if len(df) else only_green
    df = df.merge(_universe(market), on="firm_id", how="left", suffixes=("", "_univ"))
    if "sector_univ" in df.columns:
        df["sector"] = df["sector"].fillna(df.pop("sector_univ"))
    if "ticker" not in df.columns:
        df["ticker"] = df["firm_id"]
    df["region"] = _region(df, market)
    df["market"] = market
    return df.sort_values("firm_id").reset_index(drop=True)
