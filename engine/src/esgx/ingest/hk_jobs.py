"""Shardable jobs for the streaming Hong Kong ingest (local runs and Cloud Run Jobs).

A job is split into `n` shards; shard `i` takes every n-th firm of the selection and writes its
own part files, so parallel tasks never write to the same file:

  data/processed/hk_reports/part-0003-of-0020.parquet      report index
  data/processed/hk_kpi_pages/part-0003-of-0020.parquet    pages with ESG figures
  data/processed/hk_emission_rows/part-0003-of-0020.parquet  extracted rows before consolidation
  data/processed/hk_failures/part-0003-of-0020.jsonl       reports that could not be processed

A local run is shard 0 of 1. Cloud Run sets CLOUD_RUN_TASK_INDEX / CLOUD_RUN_TASK_COUNT, which
`shard_from_env` reads. Text key figures are one JSON per document and model answers one cache file
per report, so those need no sharding. `read_parts` also reads the single-file tables written
before sharding existed. `merge_emissions` consolidates all rows into `emissions_hk.parquet`.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR
from esgx.ingest import emissions_hk as eh
from esgx.ingest import hk_stream as st
from esgx.ingest.hkexnews import list_reports

Shard = tuple[int, int]


def shard_from_env(arg: str | None = None) -> Shard:
    """'3/20' -> (3, 20); without an argument the Cloud Run task variables, else (0, 1)."""
    if arg:
        i, n = arg.split("/")
        return int(i), int(n)
    return int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0")), int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))


def take_shard(sel: pd.DataFrame, shard: Shard) -> pd.DataFrame:
    """Every n-th firm starting at i: shards are disjoint and together cover the selection."""
    i, n = shard
    if not 0 <= i < n:
        raise ValueError(f"shard {i}/{n} is out of range")
    return sel.sort_values("stock_code").iloc[i::n]


def part_path(name: str, shard: Shard, ext: str = "parquet") -> Path:
    d = PROCESSED_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d / f"part-{shard[0]:04d}-of-{shard[1]:04d}.{ext}"


def read_parts(name: str, columns: list[str] | None = None) -> pd.DataFrame:
    """All parts of a table plus the pre-sharding single file `<name>.parquet`, if present."""
    files = sorted((PROCESSED_DIR / name).glob("part-*.parquet")) + [p for p in [PROCESSED_DIR / f"{name}.parquet"] if p.exists()]
    frames = [pd.read_parquet(f) for f in files]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns or [])


def _own(name: str, shard: Shard, columns: list[str]) -> pd.DataFrame:
    p = part_path(name, shard)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=columns)


def _listed(stock_id: int, start: str, attempts: int = 4) -> list[dict]:
    """HKEXnews title search, retried with a growing pause (connection drops, DNS hiccups)."""
    for k in range(attempts):
        try:
            return list_reports(stock_id, start=start)
        except Exception:
            if k == attempts - 1:
                raise
            time.sleep(5 * 2**k)
    return []


def _process(firm_id: str, rep: dict, failures: Path):
    try:
        return st.process_report(firm_id, rep)
    except Exception as e:  # noqa: BLE001 - one broken PDF must not stop the task; it is recorded for a rerun
        with failures.open("a") as f:
            f.write(json.dumps({"firm_id": firm_id, "url": rep["url"], "title": rep["title"], "error": f"{type(e).__name__}: {e}"}) + "\n")
        return None


def documents(sel: pd.DataFrame, start: str, shard: Shard = (0, 1), workers: int = 4, chunk: int = 8) -> None:
    """Stream the reports of this shard's firms; `workers` reports at a time, saved every `chunk` firms."""
    reports, pages = _own("hk_reports", shard, st.REPORT_COLS), _own("hk_kpi_pages", shard, st.PAGE_COLS)
    seen = set(read_parts("hk_reports", st.REPORT_COLS)["url"])  # any shard, any earlier run
    failures = part_path("hk_failures", shard, "jsonl")
    rows = [r for r in take_shard(sel, shard).itertuples() if pd.notna(r.hkex_sid)]
    unlisted: list[str] = []
    print(f"shard {shard[0]}/{shard[1]}: {len(rows)} firms, {len(seen)} reports already stored", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for k in range(0, len(rows), chunk):
            todo = []
            for r in rows[k:k + chunk]:
                try:
                    todo += [(r.firm_id, rep) for rep in _listed(int(r.hkex_sid), start) if rep["url"] not in seen]
                except Exception as e:  # noqa: BLE001 - a listing error for one firm must not stop the task
                    unlisted.append(r.firm_id)
                    print(f"skip {r.firm_id}: {type(e).__name__}: {str(e)[:120]}", flush=True)
            done = [x for x in pool.map(lambda a: _process(*a, failures), todo) if x is not None]
            if done:
                reports = pd.concat([reports, pd.DataFrame([d[0] for d in done])], ignore_index=True)
                pages = pd.concat([pages, pd.DataFrame([p for d in done for p in d[1]])], ignore_index=True)
                reports.to_parquet(part_path("hk_reports", shard), index=False)
                pages.to_parquet(part_path("hk_kpi_pages", shard), index=False)
                seen |= {d[0]["url"] for d in done}
            print(f"firms {min(k + chunk, len(rows))}/{len(rows)}: +{len(done)} reports, {len(todo) - len(done)} failed, {len(reports)} in this shard", flush=True)
    if unlisted:  # non-zero exit so Cloud Run retries the task; stored reports are skipped on the retry
        raise SystemExit(f"{len(unlisted)} firms could not be listed: {unlisted[:10]}")


def emission_docs(sel: pd.DataFrame, shard: Shard) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(preferred report per firm-year for this shard's firms, all stored KPI pages)."""
    reports, pages = read_parts("hk_reports", st.REPORT_COLS), read_parts("hk_kpi_pages", st.PAGE_COLS)
    firms = take_shard(sel, shard)["firm_id"]
    return st.pick_reports(reports[reports["firm_id"].isin(firms)].drop_duplicates("url")), pages


def emissions(sel: pd.DataFrame, firms: pd.DataFrame, model: str, shard: Shard = (0, 1), workers: int = 2) -> None:
    """LLM extraction of scope 1 / 2 from the stored GHG pages; answers are cached per report and model."""
    docs, pages = emission_docs(sel, shard)
    names, client = firms.set_index("firm_id")["name"], eh.LiveExtractClient(model=model)

    def one(d) -> list[dict]:
        doc = pd.Series(d._asdict())
        try:
            ex, _ = eh.extract_pages(client, names[d.firm_id], doc, st.chosen_pages(pages, d.url), st.cache_key(doc))
        except Exception as e:  # noqa: BLE001 - recorded; the cache makes a rerun resume here
            print(f"failed {d.firm_id} FY{d.fiscal_year}: {type(e).__name__}: {e}", flush=True)
            return []
        return eh.rows_from_extraction(doc, ex) if ex is not None else []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = [r for out in pool.map(one, list(docs.itertuples())) for r in out]
    pd.DataFrame(rows).to_parquet(part_path("hk_emission_rows", shard), index=False)
    print(f"shard {shard[0]}/{shard[1]}: {len(docs)} reports, {len(rows)} firm-year rows extracted with {model}", flush=True)


def merge_emissions() -> pd.DataFrame:
    """Consolidate all shards' rows to one row per firm-year and merge into `emissions_hk.parquet`."""
    rows = read_parts("hk_emission_rows")
    if rows.empty:
        raise SystemExit("no extracted rows: run the emissions step first")
    em, out = eh.consolidate(rows), PROCESSED_DIR / "emissions_hk.parquet"
    if out.exists():
        old = pd.read_parquet(out)
        em = pd.concat([old[~old["firm_id"].isin(em["firm_id"])], em], ignore_index=True)
    em.to_parquet(out, index=False)
    em.to_csv(OUTPUT_DIR / "emissions_hk.csv", index=False)
    print(f"emissions: {len(em)} firm-years for {em['firm_id'].nunique()} firms", flush=True)
    return em
