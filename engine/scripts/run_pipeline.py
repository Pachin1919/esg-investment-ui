"""Run an agentic pipeline spec from the command line (same orchestrator as the dashboard).

Examples
  .venv/bin/python scripts/run_pipeline.py --tickers XOM --mode dry_run
  .venv/bin/python scripts/run_pipeline.py --config configs/pipeline/strict-scorer.json --tickers XOM NEE --mode cache_only
  .venv/bin/python scripts/run_pipeline.py --tickers XOM --mode live          # needs MOONSHOT_API_KEY (kimi-k3), asks above 20 USD
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from esgx.agents.pipeline import Orchestrator, PipelineSpec, default_pipeline, estimate_cost


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="pipeline spec JSON (default: the built-in default pipeline)")
    ap.add_argument("--tickers", nargs="+", required=True)
    ap.add_argument("--mode", choices=["dry_run", "cache_only", "live"], default="dry_run")
    ap.add_argument("--yes", action="store_true", help="skip the cost confirmation in live mode")
    args = ap.parse_args()

    spec = PipelineSpec.model_validate_json(Path(args.config).read_text()) if args.config else default_pipeline()
    if args.mode == "live":
        years = max(1, 2026 - int(spec.start[:4]))
        est = estimate_cost(spec, len(args.tickers) * years * 4, len(args.tickers) * years)
        print(f"estimated cost: {est['total_usd']} USD")
        if est["total_usd"] > 20 and not args.yes and input("continue? [y/N] ").lower() != "y":
            return
    run = Orchestrator().start(spec, [t.upper() for t in args.tickers], args.mode, blocking=True)
    for line in run.log:
        print(f"{line['t']} [{line['stage']}] {line['msg']}")
    print(f"\nstatus: {run.status}" + (f" ({run.error})" if run.error else ""))
    print(json.dumps({k: v for k, v in run.stages.items()}, indent=1))
    for fy in run.results.get("firm_years", []):
        print(f"{fy['firm_id']} {fy['year']}: talk {fy['talk']:.2f} walk {fy['walk']:.2f} gap {fy['gap']:.2f}")
    print(f"outputs: {run.results.get('dir')}")


if __name__ == "__main__":
    main()
