"""Run the Kimi agents for Hong Kong-listed firms and write outputs/kimi_agents/sources.csv.

  .venv/bin/python kimi-agents/run.py --tickers 0883.HK 0386.HK                 # live, needs MOONSHOT_API_KEY in .env
  .venv/bin/python kimi-agents/run.py --tickers 0883.HK --dry-run               # keyword heuristics, no model calls
  .venv/bin/python kimi-agents/run.py --tickers 0883.HK --agents reports news
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kimi_agents import about_page, news, reports
from kimi_agents.client import has_key
from kimi_agents.sources import sources_frame

from esgx.config import OUTPUT_DIR
from esgx.ingest.universe_hk import load_universe_hk

AGENTS = ("reports", "about_page", "news")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", required=True, help="HK tickers as in the universe, e.g. 0883.HK")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--agents", nargs="+", choices=AGENTS, default=list(AGENTS))
    ap.add_argument("--max-news", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="keyword heuristics instead of the model; never a result")
    args = ap.parse_args()
    live = not args.dry_run
    if live and not has_key() and set(args.agents) & {"about_page", "news"}:
        raise SystemExit("MOONSHOT_API_KEY is not set: add it to .env or pass --dry-run")

    firms = load_universe_hk().set_index("firm_id")
    rows: list[dict] = []
    for t in args.tickers:
        if t not in firms.index:
            print(f"{t}: not in the Hang Seng universe, skipped")
            continue
        name = firms.loc[t, "name"]
        if "reports" in args.agents:
            found = reports.run(t, int(firms.loc[t, "hkex_sid"]), start=args.start)
            rows += found
            print(f"{t} reports: {len(found)}")
        if "about_page" in args.agents:
            found, msg = about_page.run(t, name, live=live)
            rows += found
            print(f"{t} about_page: {msg}")
        if "news" in args.agents:
            found, msg = news.run(t, name, args.start, live=live, max_records=args.max_news)
            rows += found
            print(f"{t} news: {msg}")
    out = OUTPUT_DIR / "kimi_agents"
    out.mkdir(parents=True, exist_ok=True)
    table = sources_frame(rows)
    table.to_csv(out / "sources.csv", index=False)
    if len(table):
        print(table.groupby(["firm_id", "source_type"]).size().to_string())
    print(f"-> {out / 'sources.csv'}")


if __name__ == "__main__":
    main()
