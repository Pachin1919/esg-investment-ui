"""Deterministic talk / walk / greenwashing scores (no LLM, no API key).

g    : greenness g = -(10 - walk) * E_weight / 100 from the same walk score (det_greenness*.csv)
walk : hard data only (scope 1+2 intensity vs revenue) for every firm with extracted figures
talk : claim-word intensity from the stored per-report key figures (data/processed/text_metrics)
flag : greenwasher = top-quintile talk and bottom-tercile walk within industry × year
gap  : talk − walk (secondary), plus diagnostics and the predictive validation

  .venv/bin/python scripts/score_deterministic.py --universe hk     # HKEX reports + extracted scope 1+2 (run ingest_hk_stream.py first)
  .venv/bin/python scripts/score_deterministic.py --universe hk --index hsci
  .venv/bin/python scripts/score_deterministic.py --universe tw     # walk for all TWSE/TPEx-listed firms from the exchanges' open ESG data
  .venv/bin/python scripts/score_deterministic.py --walk-only

Outputs: outputs/det_walk{sfx}.csv, det_talk{sfx}.csv, det_greenwashing{sfx}.csv, det_diagnostics{sfx}.csv,
det_validation{sfx}.csv, det_greenness{sfx}.csv (sfx = _hk / _tw). Hong Kong covers HKEX-listed
mainland China firms; US assets are never scored (scope decision 2026-10-03).
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR
from esgx.ingest.twse_esg import load_emissions_tw, load_fundamentals_tw, load_universe_tw
from esgx.ingest.universe_hk import load_universe_hk
from esgx.measures.carbon import carbon_intensity
from esgx.measures.greenness import greenness_table, scores_from_walk
from esgx.measures.greenwash import diagnostics, greenwashing_table
from esgx.measures.talk_dict import firm_year_intensity, talk_score
from esgx.measures.text_metrics import load_metrics
from esgx.measures.validation import emissions_outcomes, predictive_regression
from esgx.measures.walk_hard import walk_score
from esgx.measures.walk_pillars import walk_pillars


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["hk", "tw"], default="hk")
    ap.add_argument("--index", choices=["hsi", "hsci"], default="hsi", help="Hong Kong universe: Hang Seng Index or Composite proxy")
    ap.add_argument("--multi-walk", action="store_true", help="headline walk = equal-weight mean of carbon, water, waste and energy pillars")
    ap.add_argument("--walk-only", action="store_true")
    args = ap.parse_args()
    mkt, sfx = args.universe, f"_{args.universe}"

    if mkt == "tw":  # TWSE/TPEx open ESG data: structured scope 1 / 2 for every listed firm, latest year
        firms, emissions, fundamentals = load_universe_tw(), load_emissions_tw(), load_fundamentals_tw()
    else:  # Hong Kong: no emissions registry — figures extracted from the firms' own reports
        firms = load_universe_hk(index=args.index)
        emissions = pd.read_parquet(PROCESSED_DIR / "emissions_hk.parquet")
        fundamentals = pd.read_parquet(RAW_DIR / ("fundamentals_yf_hk.parquet" if args.index == "hsi" else f"fundamentals_yf_{args.index}.parquet"))
    emissions["scope12"] = emissions["scope1"].fillna(0) + emissions["scope2"].fillna(0)  # purchased electricity dominates for property, electronics and resorts
    carbon = carbon_intensity(emissions, fundamentals, scope="scope12")
    walk = walk_score(carbon, firms)
    if "verified" in emissions:  # third-party assurance of the figures behind the score
        walk = walk.merge(emissions[["firm_id", "year", "verified"]], on=["firm_id", "year"], how="left")
    walk = walk_pillars(walk, emissions, carbon)  # water, waste, renewable share next to carbon -> walk_multi
    if args.multi_walk:  # use the multi-pillar score as the headline walk (E_score, flag); carbon stays in pillar_carbon
        walk["walk"] = walk["walk_multi"]
    walk.to_csv(OUTPUT_DIR / f"det_walk{sfx}.csv", index=False)
    # greenness from the same number: E_score = walk, E_weight = how emission-heavy the industry is (PST 2022)
    green = greenness_table(scores_from_walk(walk), firms)
    green.to_csv(OUTPUT_DIR / f"det_greenness{sfx}.csv", index=False)
    print(f"walk: {len(walk)} firm-years, {walk['firm_id'].nunique()} firms -> outputs/det_walk{sfx}.csv")
    if args.walk_only or mkt == "tw":  # Taiwan: no English text source wired in yet, walk only
        return

    talk = talk_score(firm_year_intensity(load_metrics("hk")), firms)
    talk.to_csv(OUTPUT_DIR / f"det_talk{sfx}.csv", index=False)
    gw = greenwashing_table(talk, walk)
    gw.to_csv(OUTPUT_DIR / f"det_greenwashing{sfx}.csv", index=False)
    print(f"talk: {len(talk)} firm-years; greenwashing table: {len(gw)} firm-years -> outputs/det_greenwashing{sfx}.csv")
    diag = diagnostics(gw)
    diag.to_csv(OUTPUT_DIR / f"det_diagnostics{sfx}.csv")
    print(diag.round(2).to_string())
    try:  # Chen (2025) eq. 1: talk must not predict next-year emissions
        oc = emissions_outcomes(emissions.assign(scope1=emissions["scope12"]), fundamentals)
        val = predictive_regression(gw, oc, pillars=("talk",))
        val.to_csv(OUTPUT_DIR / f"det_validation{sfx}.csv")
        print(val.round(3).to_string())
    except ValueError as e:
        print(f"validation skipped: {e}")


if __name__ == "__main__":
    main()
