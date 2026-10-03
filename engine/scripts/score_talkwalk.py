"""Score HKEX report narratives for talk vs walk (LLM rubric + dictionary measures).

Examples
  .venv/bin/python scripts/score_talkwalk.py --tickers 0005.HK 1299.HK --dry-run   # no API calls
  .venv/bin/python scripts/score_talkwalk.py                      # every picked report in hk_reports.parquet (kimi-k3, MOONSHOT_API_KEY in .env)
  .venv/bin/python scripts/score_talkwalk.py --tickers 0005.HK --model claude-opus-5   # second rater, ANTHROPIC_API_KEY
  .venv/bin/python scripts/score_talkwalk.py --cache-only         # rebuild tables from the LLM cache, no API

Outputs
  outputs/talkwalk_documents_hk.csv   one row per scored report
  outputs/talkwalk_firm_year_hk.csv   firm × year pillars talk / walk / gap (0-10) — read by scripts/score_combined.py
  data/processed/talkwalk_firm_year_hk.parquet

Universe: Hong Kong and HKEX-listed mainland China (Taiwan has no wired text source yet;
US assets are never scored, scope decision 2026-10-03). The HARD DATA block the text is
checked against comes from the firm's own extracted scope 1+2 figures (hard_data.PROVENANCE).
"""

from __future__ import annotations

import argparse

import pandas as pd
from tqdm import tqdm

from esgx.config import OUTPUT_DIR, PROCESSED_DIR
from esgx.ingest.hk_documents import report_documents, row_for_report, stored_reports
from esgx.ingest.universe_hk import load_universe_hk
from esgx.llm import PRIMARY_MODEL
from esgx.measures.hard_data import PROVENANCE, hard_data_for
from esgx.measures.talkwalk import (
    CacheOnlyClient,
    DryRunClient,
    aggregate_firm_year,
    make_client,
    score_document,
)
from esgx.measures.text_measures import text_measures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=["hk", "tw"], default="hk")
    ap.add_argument("--index", choices=["hsi", "hsci"], default="hsi", help="Hong Kong universe: Hang Seng Index or Composite proxy")
    ap.add_argument("--tickers", nargs="*", default=[], help="firm_ids (e.g. 0005.HK); default: every firm in the stored report index")
    ap.add_argument("--start", default="2020-01-01", help="earliest filing date when listing reports live (--tickers)")
    ap.add_argument("--dry-run", action="store_true", help="no API calls; keyword heuristics instead")
    ap.add_argument("--cache-only", action="store_true", help="no API calls; rebuild outputs from cached LLM responses (skips on a miss)")
    ap.add_argument("--model", default=PRIMARY_MODEL)
    ap.add_argument("--effort", default="medium")
    args = ap.parse_args()
    if args.universe == "tw":
        raise SystemExit("Taiwan has no text source wired in yet (reports are in Chinese; the rubric input and dictionaries "
                         "are English). Walk scores exist: scripts/score_deterministic.py --universe tw")

    firms = load_universe_hk(index=args.index).set_index("firm_id")
    if args.dry_run:
        client = DryRunClient()
    elif args.cache_only:
        client = CacheOnlyClient(model=args.model)
    else:
        client = make_client(model=args.model, effort=args.effort)

    if args.tickers:  # live listing per firm, one picked report per firm-year
        docs = []
        for t in args.tickers:
            if t not in firms.index:
                print(f"skip {t}: not in the {args.index} universe")
                continue
            docs.append(report_documents(t, int(firms.loc[t, "stock_code"]), int(firms.loc[t, "hkex_sid"]), start=args.start))
        docs = pd.concat(docs, ignore_index=True) if docs else pd.DataFrame()
    else:  # the stored streaming-ingest index, no new HKEXnews listing
        docs = pd.DataFrame([row_for_report(r.firm_id, r._asdict()) for r in tqdm(list(stored_reports().itertuples()), desc="reports")])
    if docs.empty:
        raise SystemExit("no reports to score")

    rows = []
    for t, g in tqdm(docs.groupby("firm_id"), desc="firms"):
        name = firms.loc[t, "name"] if t in firms.index else t
        for row in g.itertuples():
            d = score_document(client, name, pd.Series(row._asdict()), hard_data_for(t, int(row.fiscal_year), market="hk"),
                               data_source=PROVENANCE["hk"])
            d.update(text_measures(row.text))
            rows.append(d)
    docs_scored = pd.DataFrame(rows)
    docs_scored.to_csv(OUTPUT_DIR / "talkwalk_documents_hk.csv", index=False)
    fy = aggregate_firm_year(docs_scored) if not docs_scored.empty else pd.DataFrame()
    fy.to_csv(OUTPUT_DIR / "talkwalk_firm_year_hk.csv", index=False)
    fy.to_parquet(PROCESSED_DIR / "talkwalk_firm_year_hk.parquet", index=False)

    usage_in = docs_scored.get("usage_input_tokens", pd.Series(dtype=float)).sum()
    usage_out = docs_scored.get("usage_output_tokens", pd.Series(dtype=float)).sum()
    print(f"\nscored {len(docs_scored)} reports, {int(docs_scored.get('skipped', pd.Series(dtype=bool)).sum())} skipped")
    if "skip_reason" in docs_scored:
        for r in docs_scored[docs_scored["skipped"]].itertuples():
            print(f"  skipped {r.form} {r.period}: {r.skip_reason}")
    print(f"tokens in/out: {int(usage_in):,} / {int(usage_out):,}")
    if not fy.empty:
        print(fy[["firm_id", "year", "talk", "walk", "gap", "n_docs"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
