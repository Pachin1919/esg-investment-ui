"""Gap variants and predictive validation for the LLM-scored talk / walk table.

Reads outputs/talkwalk_firm_year{sfx}.csv (from score_talkwalk.py or a published pipeline run),
writes outputs/talkwalk_gap_variants{sfx}.csv and, when the emissions and fundamentals tables
exist, outputs/talkwalk_validation{sfx}.csv (Chen 2025 eq. 1: next-year emissions on walk and talk).

  .venv/bin/python scripts/gap_variants.py              # Hong Kong
  .venv/bin/python scripts/gap_variants.py --universe tw
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.ingest.twse_esg import load_emissions_tw, load_fundamentals_tw, load_universe_tw
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.gap import GAP_COLUMNS, gap_variants
from esgx.measures.validation import validation_table


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["hk", "tw"], default="hk")
    ap.add_argument("--index", choices=["hsi", "hsci"], default="hsi", help="Hong Kong universe: Hang Seng Index or Composite proxy")
    ap.add_argument("--firm-year", default=None, help="defaults to outputs/talkwalk_firm_year{sfx}.csv")
    args = ap.parse_args()
    sfx = f"_{args.universe}"

    fy = pd.read_csv(args.firm_year or OUTPUT_DIR / f"talkwalk_firm_year{sfx}.csv")
    firms = load_universe_hk(index=args.index) if args.universe == "hk" else load_universe_tw()
    out = gap_variants(fy, firms)
    p = OUTPUT_DIR / f"talkwalk_gap_variants{sfx}.csv"
    out.to_csv(p, index=False)
    print(f"{len(out)} firm-years -> {p}")
    print(out[["firm_id", "year", "talk", "walk", *GAP_COLUMNS]].to_string(index=False))

    if args.universe == "hk":
        em = PROCESSED_DIR / "emissions_hk.parquet"
        fu = RAW_DIR / ("fundamentals_yf_hk.parquet" if args.index == "hsi" else f"fundamentals_yf_{args.index}.parquet")
        if not (em.exists() and fu.exists()):
            print("no emissions / fundamentals tables: validation skipped")
            return
        emissions, fundamentals = pd.read_parquet(em), pd.read_parquet(fu)
    else:
        emissions, fundamentals = load_emissions_tw(), load_fundamentals_tw()
    emissions["scope1"] = emissions["scope1"].fillna(0) + emissions["scope2"].fillna(0)  # validate against scope 1+2, the walk input
    try:
        tab = validation_table(out, emissions, fundamentals)
    except ValueError as e:  # too few scored firms with matched emissions
        print(f"validation skipped: {e}")
        return
    tab.to_csv(OUTPUT_DIR / f"talkwalk_validation{sfx}.csv")
    print(tab.round(3).to_string())


if __name__ == "__main__":
    main()
