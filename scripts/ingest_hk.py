"""Hong Kong (Hang Seng Index) ingest: universe, prices, factors, fundamentals, reports, emissions.

Steps (each cached; --refresh re-downloads):
  1. universe      HSI constituents + yfinance sector + HKEX stock ids   -> data/raw/universe_hsi.parquet
  2. prices        monthly returns / mktcap (HKD)                          -> data/raw/prices_monthly_hk.parquet
  3. factors       Ken French Asia Pacific ex Japan FF5 + MOM              -> data/raw/factors_monthly_asia_pacific_ex_japan.parquet
  4. fundamentals  revenue / book equity from yfinance, USD millions       -> data/raw/fundamentals_yf_hk.parquet
  5. documents     ESG + annual report PDFs from HKEXnews (+ page text)    -> data/processed/documents_hk.parquet
  6. emissions     scope 1/2 via LLM extraction (needs ANTHROPIC_API_KEY)  -> data/processed/emissions_hk.parquet

Examples
  .venv/bin/python scripts/ingest_hk.py --steps universe prices factors fundamentals
  .venv/bin/python scripts/ingest_hk.py --steps documents --max-firms 5 --start 2023-01-01
  .venv/bin/python scripts/ingest_hk.py --steps emissions --max-firms 5 --dry-run   # cost estimate only
  .venv/bin/python scripts/ingest_hk.py --steps documents --sectors Utilities Energy "Basic Materials" Industrials "Real Estate"
"""

from __future__ import annotations

import argparse

import pandas as pd
from tqdm import tqdm

from esgx.config import OUTPUT_DIR, PROCESSED_DIR
from esgx.ingest.emissions_hk import (
    ClaudeExtractClient,
    consolidate,
    extract_document,
    rows_from_extraction,
)
from esgx.ingest.factors import load_factors
from esgx.ingest.fundamentals_yf import load_fundamentals_yf
from esgx.ingest.hkexnews import load_documents_hk
from esgx.ingest.prices import load_prices
from esgx.ingest.universe_hk import load_universe_hk

ALL_STEPS = ["universe", "prices", "factors", "fundamentals", "documents", "emissions"]


def pick_docs(docs: pd.DataFrame) -> pd.DataFrame:
    """Per firm and fiscal year keep the standalone ESG report if there is one, else the annual report."""
    pref = docs.assign(_t=docs["doc_type"].map({"esg_report": 1, "annual_report": 0}))
    pref = pref.sort_values(["firm_id", "fiscal_year", "_t", "filing_date"], ascending=[True, True, False, False])
    return pref.drop_duplicates(["firm_id", "fiscal_year"]).drop(columns="_t").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", default=ALL_STEPS, choices=ALL_STEPS)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--max-firms", type=int, default=None, help="limit documents/emissions to the first N firms (by stock code)")
    ap.add_argument("--sectors", nargs="*", default=[], help="limit documents/emissions to these yfinance sectors")
    ap.add_argument("--start", default="2022-01-01", help="earliest filing date for reports")
    ap.add_argument("--dry-run", action="store_true", help="emissions: only count candidate pages / estimate cost, no API calls")
    ap.add_argument("--model", default="claude-opus-5")
    args = ap.parse_args()
    lines: list[str] = ["# Hong Kong ingest report\n"]

    firms = load_universe_hk(refresh=args.refresh and "universe" in args.steps)
    lines.append(f"Universe: {len(firms)} HSI constituents. Sectors:\n\n" + firms["sector"].value_counts().to_frame("n").to_markdown() + "\n")
    print(lines[-1])

    if "prices" in args.steps:
        px = load_prices(firms["firm_id"].tolist(), refresh=args.refresh, cache_name="prices_monthly_hk")
        lines.append(f"Prices: {px['firm_id'].nunique()} firms, {px['month'].min()} to {px['month'].max()}, mktcap coverage {px['mktcap'].notna().mean():.0%}.\n")
        print(lines[-1])
    if "factors" in args.steps:
        f = load_factors(refresh=args.refresh, region="asia_pacific_ex_japan")
        lines.append(f"Factors (AP ex JP): {f['month'].min()} to {f['month'].max()}, mean mkt_rf {f['mkt_rf'].mean() * 1e4:.0f} bps/month.\n")
        print(lines[-1])
    if "fundamentals" in args.steps:
        fu = load_fundamentals_yf(firms, refresh=args.refresh, cache_name="fundamentals_yf_hk")
        cov = fu.dropna(subset=["revenue"]).groupby("year")["firm_id"].nunique()
        lines.append("Fundamentals (yfinance): firms with revenue by year:\n\n" + cov.to_frame("n").to_markdown() + "\n")
        print(lines[-1])

    sel = firms.sort_values("stock_code")
    if args.sectors:
        sel = sel[sel["sector"].isin(args.sectors)]
    if args.max_firms:
        sel = sel.head(args.max_firms)

    if "documents" in args.steps:
        rows = []
        for r in tqdm(list(sel.itertuples()), desc="hkexnews"):
            if pd.isna(r.hkex_sid):
                continue
            rows.append(load_documents_hk(r.firm_id, int(r.stock_code), int(r.hkex_sid), start=args.start))
        docs = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        old_p = PROCESSED_DIR / "documents_hk.parquet"
        if old_p.exists():  # merge with earlier runs (other firms)
            old = pd.read_parquet(old_p)
            docs = pd.concat([old[~old["firm_id"].isin(docs["firm_id"])], docs], ignore_index=True)
        docs.to_parquet(old_p, index=False)
        lines.append(f"Documents: {len(docs)} reports for {docs['firm_id'].nunique()} firms.\n\n" + docs.groupby(["doc_type", "fiscal_year"]).size().to_frame("n").to_markdown() + "\n")
        print(lines[-1])

    if "emissions" in args.steps:
        docs = pick_docs(pd.read_parquet(PROCESSED_DIR / "documents_hk.parquet"))
        docs = docs[docs["firm_id"].isin(sel["firm_id"])]
        names = firms.set_index("firm_id")["name"]
        if args.dry_run:
            from pathlib import Path

            from esgx.config import anthropic_client
            from esgx.ingest.emissions_hk import SYSTEM_PROMPT, _user_prompt, candidate_pages
            from esgx.ingest.hkexnews import pdf_pages
            c = anthropic_client()
            tot = 0
            for d in docs.itertuples():
                chosen = candidate_pages(pdf_pages(Path(d.path)))
                n = c.messages.count_tokens(model=args.model, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": _user_prompt(names[d.firm_id], d.title, int(d.fiscal_year), chosen)}]).input_tokens if chosen else 0
                tot += n
                print(f"{d.firm_id} FY{d.fiscal_year} {d.doc_type:13s} pages={[i for i, _ in chosen]} tokens={n:,}")
            print(f"\n{len(docs)} documents, {tot:,} input tokens, ~USD {tot * 5 / 1e6 + len(docs) * 1500 * 25 / 1e6:.2f} with {args.model}")
            return
        client = ClaudeExtractClient(model=args.model)
        rows, usage_in, usage_out = [], 0, 0
        for d in tqdm(list(docs.itertuples()), desc="extract"):
            ex, usage = extract_document(client, names[d.firm_id], pd.Series(d._asdict()))
            usage_in += usage["input_tokens"]
            usage_out += usage["output_tokens"]
            if ex is not None:
                rows.extend(rows_from_extraction(pd.Series(d._asdict()), ex))
        em = consolidate(pd.DataFrame(rows))
        old_p = PROCESSED_DIR / "emissions_hk.parquet"
        if old_p.exists():
            old = pd.read_parquet(old_p)
            em = pd.concat([old[~old["firm_id"].isin(em["firm_id"])], em], ignore_index=True)
        em.to_parquet(old_p, index=False)
        em.to_csv(OUTPUT_DIR / "emissions_hk.csv", index=False)
        show = em[["firm_id", "year", "scope1", "scope2", "scope2_basis", "verified", "confidence", "pages", "doc_type"]].sort_values(["firm_id", "year"])
        lines.append(f"Emissions: {len(em)} firm-years for {em['firm_id'].nunique()} firms (tokens in/out {usage_in:,}/{usage_out:,}).\n\n" + show.to_markdown(index=False) + "\n")
        print(lines[-1])

    (OUTPUT_DIR / "hk_ingest_report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
