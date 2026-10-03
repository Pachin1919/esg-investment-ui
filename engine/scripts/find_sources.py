"""Find where a firm's text lives: reports (exchange archive), about page (website), news (GDELT).

Runs only the three source-finder agents of the pipeline plus the aggregator, and writes
outputs/pipeline_runs/<run>/sources.csv.

Examples
  .venv/bin/python scripts/find_sources.py --tickers 0002.HK 0883.HK --universe hk --mode dry_run   # keyword heuristics, free
  .venv/bin/python scripts/find_sources.py --tickers 0002.HK --universe hk --mode live              # kimi-k3 picks and labels
"""

from __future__ import annotations

import argparse

import pandas as pd

from esgx.agents.pipeline import Orchestrator, default_pipeline

FINDERS = ("find_reports", "find_about_page", "find_news")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", required=True)
    ap.add_argument("--universe", choices=["us", "hk"], default="hk")
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--mode", choices=["dry_run", "live"], default="dry_run")
    ap.add_argument("--only", nargs="+", choices=FINDERS, default=list(FINDERS))
    ap.add_argument("--max-news", type=int, default=50)
    args = ap.parse_args()

    spec = default_pipeline()
    spec.universe, spec.start = args.universe, args.start
    for s in spec.stages:
        s.enabled = s.kind in args.only or s.kind == "aggregate"
        if s.kind == "find_news":
            s.params["max_records"] = args.max_news
    run = Orchestrator().start(spec, args.tickers, args.mode, blocking=True)
    for line in run.log:
        print(f"{line['t']} [{line['stage']}] {line['msg']}")
    print(f"\nstatus: {run.status}" + (f" ({run.error})" if run.error else ""))
    src = pd.DataFrame(run.results.get("sources", []))
    if len(src):
        print(src.groupby(["firm_id", "source_type"]).size().to_string())
    print(f"outputs: {run.results.get('dir')}")


if __name__ == "__main__":
    main()
