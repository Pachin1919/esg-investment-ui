"""Deterministic talk / walk / greenwashing scores (no LLM, no API key).

walk : hard data only (GHGRP scope-1 intensity, SEC revenue) for every registry-matched firm
talk : claim-word intensity over each firm's filings, risk-context hits dropped (EDGAR, cached)
flag : greenwasher = top-quintile talk and bottom-tercile walk within industry × year
gap  : talk − walk (secondary), plus diagnostics and the predictive validation

  .venv/bin/python scripts/score_deterministic.py --sectors Energy Utilities Materials --start 2021-01-01
  .venv/bin/python scripts/score_deterministic.py --tickers XOM NEE DUK --forms 10-K 8-K
  .venv/bin/python scripts/score_deterministic.py --walk-only
  .venv/bin/python scripts/score_deterministic.py --universe hk     # HKEX reports + extracted scope 1+2 (run ingest_hk.py first)

Outputs: outputs/det_walk.csv, det_talk.csv, det_greenwashing.csv, det_diagnostics.csv, det_validation.csv (suffix _hk for Hong Kong)
"""

from __future__ import annotations

import argparse

import pandas as pd
from tqdm import tqdm

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.ingest.universe import load_universe
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.carbon import carbon_intensity
from esgx.measures.greenwash import diagnostics, greenwashing_table
from esgx.measures.talk_dict import collect_us_counts, filing_counts, firm_year_intensity, report_counts, talk_score
from esgx.measures.validation import emissions_outcomes, predictive_regression
from esgx.measures.walk_hard import walk_score


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["us", "hk"], default="us")
    ap.add_argument("--tickers", nargs="*", default=[])
    ap.add_argument("--sectors", nargs="*", default=[], help="GICS sectors; only firms with matched emissions are fetched")
    ap.add_argument("--start", default="2021-01-01", help="earliest 10-K filing date")
    ap.add_argument("--forms", nargs="+", default=["10-K"], help="10-K and/or 8-K (press releases)")
    ap.add_argument("--max-8k", type=int, default=20)
    ap.add_argument("--walk-only", action="store_true")
    args = ap.parse_args()
    hk = args.universe == "hk"
    sfx = "_hk" if hk else ""

    if hk:  # no emissions registry: figures extracted from the firms' own reports, scope 1 + 2 (electricity dominates)
        firms = load_universe_hk()
        emissions = pd.read_parquet(PROCESSED_DIR / "emissions_hk.parquet")
        emissions["scope12"] = emissions["scope1"].fillna(0) + emissions["scope2"].fillna(0)
        fundamentals = pd.read_parquet(RAW_DIR / "fundamentals_yf_hk.parquet")
    else:
        firms = load_universe()
        emissions, fundamentals = pd.read_parquet(PROCESSED_DIR / "emissions.parquet"), pd.read_parquet(RAW_DIR / "fundamentals.parquet")
    carbon = carbon_intensity(emissions, fundamentals, scope="scope12" if hk else "scope1")
    walk = walk_score(carbon, firms)
    walk.to_csv(OUTPUT_DIR / f"det_walk{sfx}.csv", index=False)
    print(f"walk: {len(walk)} firm-years, {walk['firm_id'].nunique()} firms -> outputs/det_walk{sfx}.csv")
    if args.walk_only:
        return

    counts = report_counts(pd.read_parquet(PROCESSED_DIR / "documents_hk.parquet")) if hk else collect_us_counts(firms, set(walk["firm_id"]), args.tickers, args.sectors, tuple(args.forms), args.start, args.max_8k)
    talk = talk_score(firm_year_intensity(counts), firms)
    talk.to_csv(OUTPUT_DIR / f"det_talk{sfx}.csv", index=False)
    gw = greenwashing_table(talk, walk)
    gw.to_csv(OUTPUT_DIR / f"det_greenwashing{sfx}.csv", index=False)
    print(f"talk: {len(talk)} firm-years; greenwashing table: {len(gw)} firm-years -> outputs/det_greenwashing{sfx}.csv")
    diag = diagnostics(gw)
    diag.to_csv(OUTPUT_DIR / f"det_diagnostics{sfx}.csv")
    print(diag.round(2).to_string())
    try:  # Chen (2025) eq. 1: talk must not predict next-year emissions
        oc = emissions_outcomes(emissions.assign(scope1=emissions["scope12"]) if hk else emissions, fundamentals)
        val = predictive_regression(gw, oc, pillars=("talk",))
        val.to_csv(OUTPUT_DIR / f"det_validation{sfx}.csv")
        print(val.round(3).to_string())
    except ValueError as e:
        print(f"validation skipped: {e}")


if __name__ == "__main__":
    main()
