"""Monthly FX rates for cross-market recommendations (base currency HKD).

Writes data/raw/fx_monthly.parquet (month, pair, rate), e.g. TWDHKD = HKD per 1 TWD.

    python scripts/ingest_fx.py [--refresh]
"""

from __future__ import annotations

import argparse

from esgx.ingest.fx import load_fx


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    df = load_fx(refresh=args.refresh)
    for pair, d in df.groupby("pair"):
        print(f"{pair}: {len(d)} months {d['month'].min()}..{d['month'].max()}, last rate {d['rate'].iloc[-1]:.5f}")
    print("-> data/raw/fx_monthly.parquet")


if __name__ == "__main__":
    main()
