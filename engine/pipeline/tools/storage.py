"""Storage tools: universes, processed tables, run outputs. All local files under data/ and outputs/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR
from esgx.ingest.twse_esg import load_universe_tw as _twse
from esgx.ingest.universe_hk import load_universe_hk as _hk
from esgx.measures import talkwalk as _tw
from pipeline.tools.base import tool


@tool(kind="storage", cost="free")
def load_universe(universe: str = "hk") -> pd.DataFrame:
    """Firm table (firm_id, name, sector, stock_code / hkex_sid) for 'hk' (Hang Seng) or 'tw' (TWSE + TPEx)."""
    if universe == "hk":
        return _hk()
    if universe == "tw":
        return _twse()
    raise ValueError(f"unknown universe {universe!r} (hk and tw exist; US assets are never used)")


@tool(kind="storage", cost="free")
def read_processed(name: str) -> pd.DataFrame:
    """Read data/processed/<name>.parquet (empty frame if missing)."""
    p = PROCESSED_DIR / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@tool(kind="storage", cost="free")
def write_run_output(run_dir: Path, name: str, obj: pd.DataFrame | list | dict) -> Path:
    """Write a DataFrame (csv) or JSON-able object (json) into the run's output directory."""
    run_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, pd.DataFrame):
        p = run_dir / f"{name}.csv"
        obj.to_csv(p, index=False)
    else:
        p = run_dir / f"{name}.json"
        p.write_text(json.dumps(obj, indent=1, default=str))
    return p


@tool(kind="storage", cost="free")
def publish_talkwalk(documents: pd.DataFrame | None, firm_year: pd.DataFrame, universe: str = "hk") -> list[Path]:
    """Overwrite the dashboard's outputs/talkwalk_{documents,firm_year}_<universe>.csv (explicit opt-in)."""
    out = []
    if documents is not None:
        p = OUTPUT_DIR / f"talkwalk_documents_{universe}.csv"
        documents.to_csv(p, index=False)
        out.append(p)
    p = OUTPUT_DIR / f"talkwalk_firm_year_{universe}.csv"
    firm_year.to_csv(p, index=False)
    out.append(p)
    return out


@tool(kind="compute", cost="free")
def aggregate_firm_year(scores: pd.DataFrame, form_weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Document scores -> firm x year talk / walk / gap, climate-relevance weighted, equal form weights by default."""
    return _tw.aggregate_firm_year(scores, form_weights=form_weights)


def to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(df.to_json(orient="records")) if len(df) else []
