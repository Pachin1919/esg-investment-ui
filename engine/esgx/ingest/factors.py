"""Ken French monthly factors: FF5 (2x3) + momentum, converted from % to decimal.

Regions: "us" (default) and "asia_pacific_ex_japan" (covers Hong Kong; RF is the US
one-month T-bill in both files, returns in USD).
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

from esgx.config import RAW_DIR
from esgx.schema import validate

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
REGIONS = {
    "us": ("F-F_Research_Data_5_Factors_2x3_CSV.zip", "F-F_Momentum_Factor_CSV.zip"),
    "asia_pacific_ex_japan": ("Asia_Pacific_ex_Japan_5_Factors_CSV.zip", "Asia_Pacific_ex_Japan_Mom_Factor_CSV.zip"),
}
FF5, MOM = REGIONS["us"]


def _read_ff_zip(name: str) -> pd.DataFrame:
    raw = requests.get(BASE + name, timeout=60).content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("latin1")
    lines = text.splitlines()
    # monthly block = first run of lines starting with a 6-digit yyyymm
    rows, header, started = [], None, False
    for ln in lines:
        s = ln.strip()
        if not started:
            if s and s.split(",")[0].strip().isdigit() and len(s.split(",")[0].strip()) == 6:
                started = True
                rows.append(s)
            elif s.startswith(","):
                header = s
            continue
        if not s or not s.split(",")[0].strip().isdigit():
            break
        rows.append(s)
    df = pd.read_csv(io.StringIO("\n".join([header or ""] + rows)))
    df = df.rename(columns={df.columns[0]: "yyyymm"})
    df["month"] = pd.PeriodIndex(df["yyyymm"].astype(str), freq="M")
    df = df.drop(columns="yyyymm")
    df.columns = [c.strip().lower().replace("-", "_") for c in df.columns]
    for c in df.columns:
        if c != "month":
            df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0
    return df


def load_factors(refresh: bool = False, region: str = "us") -> pd.DataFrame:
    if region not in REGIONS:
        raise ValueError(f"unknown region {region!r}; choose from {list(REGIONS)}")
    suffix = "" if region == "us" else f"_{region}"
    path = RAW_DIR / f"factors_monthly{suffix}.parquet"
    if path.exists() and not refresh:
        df = pd.read_parquet(path)
        df["month"] = pd.PeriodIndex(df["month"], freq="M")
        return df
    ff5_name, mom_name = REGIONS[region]
    ff5 = _read_ff_zip(ff5_name)
    mom = _read_ff_zip(mom_name)
    mom = mom.rename(columns={mom.columns[[c != "month" for c in mom.columns]][0]: "mom"})
    df = ff5.merge(mom, on="month", how="inner")
    df = df[["month", "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]]
    validate(df, "factors_monthly")
    df.assign(month=df["month"].astype(str)).to_parquet(path, index=False)
    return df
