"""Streaming Hong Kong ingest: one report at a time, keep extracted data only, discard the PDF.

Steps
  universe   constituents, sector and domicile (yfinance), revenue -> data/raw/universe_<index>.parquet,
             fundamentals_yf_<index>.parquet. --index hsi (85 firms) or hsci (Composite proxy, about 590)
  documents  list reports on HKEXnews, then per report: download -> text key figures as JSON
             (word counts, per-term hits, sentiment) -> keep the pages with ESG figures
             (GHG, energy, water, waste) -> delete the PDF
  emissions  scope 1 / 2 via LLM extraction from the stored GHG pages
             (primary model kimi-k3, needs MOONSHOT_API_KEY; --model claude-* for a second rater)
  merge      consolidate the extracted rows of all shards -> data/processed/emissions_hk.parquet

Sharding: --shard i/n takes every n-th firm and writes its own part files (see ingest/hk_jobs.py).
On Cloud Run Jobs the shard comes from CLOUD_RUN_TASK_INDEX / CLOUD_RUN_TASK_COUNT.

Examples
  .venv/bin/python scripts/ingest_hk_stream.py --steps documents --sectors Utilities Energy "Basic Materials"
  .venv/bin/python scripts/ingest_hk_stream.py --steps documents --index hsci --shard 0/4
  .venv/bin/python scripts/ingest_hk_stream.py --steps emissions --dry-run      # token estimate only
  .venv/bin/python scripts/ingest_hk_stream.py --steps emissions merge
"""

from __future__ import annotations

import argparse

from esgx import llm
from esgx.ingest import emissions_hk as eh
from esgx.ingest import hk_jobs as jobs
from esgx.ingest import hk_stream as st
from esgx.ingest.fundamentals_yf import load_fundamentals_yf
from esgx.ingest.universe_hk import load_universe_hk


def dry_run(sel, firms, model: str, shard: jobs.Shard) -> None:
    docs, pages = jobs.emission_docs(sel, shard)
    names, tot, todo = firms.set_index("firm_id")["name"], 0, 0
    for d in docs.itertuples():
        chosen = st.chosen_pages(pages, d.url)
        if not chosen or eh._cache_path(st.cache_key(d._asdict()), model).exists():
            continue
        todo += 1
        tot += (len(eh.SYSTEM_PROMPT) + len(eh._user_prompt(names[d.firm_id], d.title, int(d.fiscal_year), chosen))) // 4  # ~4 chars per token
    print(f"{len(docs)} reports, {len(docs) - todo} cached or without GHG pages, {todo} to extract with {model}: about {tot:,} input tokens (estimated at 4 characters per token)")
    if llm.provider(model) == "anthropic":
        print(f"~USD {tot * 5 / 1e6 + todo * 1500 * 25 / 1e6:.2f} at the claude-opus-5 pilot rates")
    else:
        print("cost per token for this model is not recorded in the repo; run a few reports first and read the usage")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", default=["documents"], choices=["universe", "documents", "emissions", "merge"])
    ap.add_argument("--index", choices=["hsi", "hsci"], default="hsi")
    ap.add_argument("--sectors", nargs="*", default=[])
    ap.add_argument("--tickers", nargs="*", default=[])
    ap.add_argument("--domicile", nargs="*", default=[], help="e.g. China: mainland-domiciled firms listed in Hong Kong")
    ap.add_argument("--start", default="2022-01-01", help="earliest filing date for reports")
    ap.add_argument("--shard", default=None, help="i/n: process every n-th firm starting at i (default: Cloud Run task index, else 0/1)")
    ap.add_argument("--workers", type=int, default=4, help="reports processed in parallel within this shard")
    ap.add_argument("--dry-run", action="store_true", help="emissions: token estimate only")
    ap.add_argument("--model", default=eh.DEFAULT_MODEL)
    args = ap.parse_args()
    shard = jobs.shard_from_env(args.shard)
    firms = load_universe_hk(index=args.index)
    if "universe" in args.steps:
        fu = load_fundamentals_yf(firms, cache_name="fundamentals_yf_hk" if args.index == "hsi" else f"fundamentals_yf_{args.index}")
        print(f"{args.index}: {len(firms)} firms, {firms['domicile'].value_counts().head(4).to_dict()}, revenue for {fu.dropna(subset=['revenue'])['firm_id'].nunique()} firms")
        print(firms["sector"].value_counts().to_string())
    sel = firms
    if args.sectors or args.tickers or args.domicile:
        sel = sel[sel["sector"].isin(args.sectors) | sel["firm_id"].isin(args.tickers) | sel["domicile"].isin(args.domicile)]
    if "documents" in args.steps:
        jobs.documents(sel, args.start, shard=shard, workers=args.workers)
    if "emissions" in args.steps:
        if args.dry_run:
            dry_run(sel, firms, args.model, shard)
        else:
            jobs.emissions(sel, firms, args.model, shard=shard, workers=args.workers)
    if "merge" in args.steps:
        jobs.merge_emissions()


if __name__ == "__main__":
    main()
