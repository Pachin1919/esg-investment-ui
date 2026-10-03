"""Latest close per ticker, for share counts in recommendations.

Hong Kong: every priced name. Taiwan: the three largest names of every sector — a superset
of the balanced pool (`portfolio.pool`), so every Taiwan name the app recommends by default
has a price without downloading all ~2,000 tickers.

    python scripts/ingest_last_close.py --market tw [--refresh]
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.config import RAW_DIR
from esgx.ingest.last_close import load_last_close
from esgx.portfolio.pool import eligible, largest_per_sector

UNIVERSE = {"hk": "universe_hsi.parquet", "tw": "universe_twse.parquet"}
PER_SECTOR = 3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--market", choices=["hk", "tw"], default="tw")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    prices = pd.read_parquet(RAW_DIR / f"prices_monthly_{args.market}.parquet")
    tickers = sorted(prices["firm_id"].unique())
    if args.market != "hk":
        sectors = pd.read_parquet(RAW_DIR / UNIVERSE[args.market]).drop_duplicates("firm_id").set_index("firm_id")["sector"]
        n_sectors = sectors.reindex(eligible(prices)).fillna("Unknown").nunique()
        tickers = sorted(largest_per_sector(prices, sectors, PER_SECTOR * n_sectors))
    df = load_last_close(tickers, market=args.market, refresh=args.refresh)
    print(f"{args.market}: {len(df)}/{len(tickers)} closes as of {df['date'].iloc[0]} -> data/raw/last_close_{args.market}.parquet")


if __name__ == "__main__":
    main()
