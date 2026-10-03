"""Lazy, mtime-cached access to the tables the pipeline writes.

The API never computes anything: it serves `outputs/` and `data/processed/` as they are, so
the dashboard is a view of the pipeline, not a second implementation of it. Every loader
returns an empty DataFrame when the file is missing, so the UI degrades per dataset.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from esgx.config import OUTPUT_DIR, PROCESSED_DIR, RAW_DIR

_READERS = {".csv": pd.read_csv, ".parquet": pd.read_parquet}


@dataclass
class DataStore:
    outputs: Path = OUTPUT_DIR
    processed: Path = PROCESSED_DIR
    raw: Path = RAW_DIR
    _cache: dict[Path, tuple[float, pd.DataFrame]] = field(default_factory=dict, repr=False)

    # ---------------------------------------------------------------- generic
    def table(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        mtime = path.stat().st_mtime
        hit = self._cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        df = _READERS[path.suffix](path)
        self._cache[path] = (mtime, df)
        return df

    def datasets(self) -> dict[str, dict[str, Any]]:
        """Availability of every dataset the UI knows about."""
        out = {}
        for name, path in self._paths().items():
            if path.exists():
                rows = len(self.table(path)) if path.suffix in _READERS else None
                out[name] = {"available": True, "rows": rows,
                             "updated": datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).astimezone().isoformat(timespec="seconds"),
                             "path": str(path.relative_to(path.parents[1]))}
            else:
                out[name] = {"available": False, "rows": 0, "updated": None, "path": str(path.name)}
        return out

    def _paths(self) -> dict[str, Path]:
        return {
            "talkwalk_firm_year": self.outputs / "talkwalk_firm_year_hk.csv",
            "talkwalk_documents": self.outputs / "talkwalk_documents_hk.csv",
            "greenness": self.outputs / "det_greenness_hk.csv",
            "gmb_monthly": self.outputs / "gmb_monthly_hk.csv",
            "emissions_hk": self.outputs / "emissions_hk.csv",
            "universe_hsi": self.raw / "universe_hsi.parquet",
            "universe_hsci": self.raw / "universe_hsci.parquet",
            "universe_twse": self.raw / "universe_twse.parquet",
            "fundamentals_hk": self.raw / "fundamentals_yf_hk.parquet",
            "fundamentals_tw": self.raw / "fundamentals_twse.parquet",
            "greenness_tw": self.outputs / "det_greenness_tw.csv",
            "gmb_monthly_tw": self.outputs / "gmb_monthly_tw.csv",
            "emissions_tw": self.processed / "emissions_tw.parquet",
            "prices_hk": self.raw / "prices_monthly_hk.parquet",
            "prices_tw": self.raw / "prices_monthly_tw.parquet",
            "factors_asia_pacific_ex_japan": self.raw / "factors_monthly_asia_pacific_ex_japan.parquet",
            "factors_emerging": self.raw / "factors_monthly_emerging.parquet",
            "fx_monthly": self.raw / "fx_monthly.parquet",
        }

    def prices(self, market: str = "hk") -> pd.DataFrame:
        path = self._paths().get(f"prices_{market}")
        return self.table(path) if path else pd.DataFrame()

    def fx(self, pair: str) -> pd.DataFrame:
        """Month-end rates for one pair (base currency per unit of the quoted currency)."""
        df = self.table(self._paths()["fx_monthly"])
        return df[df["pair"] == pair] if not df.empty else df

    def factors(self, region: str = "asia_pacific_ex_japan") -> pd.DataFrame:
        path = self._paths().get(f"factors_{region}")
        return self.table(path) if path else pd.DataFrame()

    # ---------------------------------------------------------------- tables
    def firms(self) -> pd.DataFrame:
        frames = []
        for key in ("universe_hsi", "universe_hsci", "universe_twse"):
            df = self.table(self._paths()[key])
            if not df.empty:
                frames.append(df[["firm_id", "name", "sector", "industry", "country"]])
        if not frames:
            return pd.DataFrame(columns=["firm_id", "name", "sector", "industry", "country"])
        firms = pd.concat(frames, ignore_index=True).drop_duplicates("firm_id")
        tw, em, gr = self.talkwalk_firm_year(), self.emissions(), self.greenness()
        firms["has_talkwalk"] = firms["firm_id"].isin(tw.get("firm_id", pd.Series(dtype=str)))
        matched = em[em["matched"]] if "matched" in em else em
        firms["has_emissions"] = firms["firm_id"].isin(matched.get("firm_id", pd.Series(dtype=str)))
        firms["has_greenness"] = firms["firm_id"].isin(gr.get("firm_id", pd.Series(dtype=str)))
        return firms.sort_values("firm_id").reset_index(drop=True)

    def talkwalk_firm_year(self) -> pd.DataFrame:
        return self.table(self._paths()["talkwalk_firm_year"])

    def talkwalk_documents(self) -> pd.DataFrame:
        return self.table(self._paths()["talkwalk_documents"])

    def greenness(self, market: str = "hk") -> pd.DataFrame:
        path = self._paths().get("greenness" if market == "hk" else f"greenness_{market}")
        return self.table(path) if path else pd.DataFrame()

    def gmb(self, market: str = "hk") -> pd.DataFrame:
        path = self._paths().get("gmb_monthly" if market == "hk" else f"gmb_monthly_{market}")
        df = self.table(path) if path else pd.DataFrame()
        if df.empty:
            return df
        df = df.copy()
        for c in ("gmb", "gmb_ew", "gmb_within", "gmb_reg"):
            if c in df:
                df[f"cum_{c}"] = (1 + df[c].fillna(0)).cumprod() - 1
        return df

    def emissions(self, market: str = "hk") -> pd.DataFrame:
        """Scope 1+2 rows for one market: HK LLM-extracted from HKEX reports, TW from the
        exchanges' open ESG data; revenue merged in for intensity."""
        em = self.table(self._paths()["emissions_hk"] if market == "hk" else self._paths()["emissions_tw"])
        cols = ["firm_id", "year", "scope1", "scope2", "scope3", "source", "matched"]
        if em.empty:
            return pd.DataFrame(columns=cols + ["scope12"])
        em = em[[c for c in cols if c in em]]
        if "matched" not in em:
            em["matched"] = True
        em["matched"] = em["matched"].fillna(True).astype(bool)
        em["scope12"] = em["scope1"].fillna(0) + em["scope2"].fillna(0)
        fu = self.table(self._paths()["fundamentals_hk"] if market == "hk" else self._paths()["fundamentals_tw"])
        if not fu.empty:
            em = em.merge(fu[["firm_id", "year", "revenue"]], on=["firm_id", "year"], how="left")
            em["intensity"] = em["scope12"] / em["revenue"]  # tCO2e per USD million revenue
        return em


def records(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict[str, Any]]:
    """DataFrame -> JSON-safe list of dicts (NaN/NaT -> None, numpy scalars -> python)."""
    if df.empty:
        return []
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    out = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            elif isinstance(v, pd.Timestamp):
                clean[k] = v.isoformat()
            elif v is pd.NaT or v is pd.NA:
                clean[k] = None
            elif hasattr(v, "item"):
                clean[k] = v.item()
            else:
                clean[k] = v
        out.append(clean)
    return out
