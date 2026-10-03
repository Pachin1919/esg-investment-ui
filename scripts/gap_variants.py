"""Gap variants and predictive validation for the scored talk / walk table.

Reads outputs/talkwalk_firm_year.csv (from score_talkwalk.py or a published pipeline run),
writes outputs/talkwalk_gap_variants.csv and, when GHGRP emissions and fundamentals exist,
outputs/talkwalk_validation.csv (Chen 2025 eq. 1: next-year emissions on walk and talk).

  .venv/bin/python scripts/gap_variants.py
  .venv/bin/python scripts/gap_variants.py --universe hk
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.ingest.universe import load_universe
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.gap import GAP_COLUMNS, gap_variants
from esgx.measures.validation import validation_table


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["us", "hk"], default="us")
    ap.add_argument("--firm-year", default=str(OUTPUT_DIR / "talkwalk_firm_year.csv"))
    args = ap.parse_args()

    fy = pd.read_csv(args.firm_year)
    firms = load_universe_hk() if args.universe == "hk" else load_universe()
    out = gap_variants(fy, firms)
    p = OUTPUT_DIR / "talkwalk_gap_variants.csv"
    out.to_csv(p, index=False)
    print(f"{len(out)} firm-years -> {p}")
    print(out[["firm_id", "year", "talk", "walk", *GAP_COLUMNS]].to_string(index=False))

    em, fu = PROCESSED_DIR / "emissions.parquet", RAW_DIR / "fundamentals.parquet"
    if not (em.exists() and fu.exists()):
        print("no emissions / fundamentals tables: validation skipped")
        return
    try:
        tab = validation_table(out, pd.read_parquet(em), pd.read_parquet(fu))
    except ValueError as e:  # too few scored firms with matched emissions
        print(f"validation skipped: {e}")
        return
    tab.to_csv(OUTPUT_DIR / "talkwalk_validation.csv")
    print(tab.round(3).to_string())


if __name__ == "__main__":
    main()
