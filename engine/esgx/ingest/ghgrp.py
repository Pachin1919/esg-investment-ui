"""EPA Greenhouse Gas Reporting Program (GHGRP) via the Envirofacts REST API.

Facility-level direct (scope 1) CO2e for US facilities emitting >25 kt/yr.
Facilities carry a `parent_company` string like "EXXON MOBIL CORP (60%); XYZ LLC (40%)".
We allocate facility emissions to parents by the stated share and match parent
names to the universe by normalised company name.

Coverage caveats (flagged in the `matched` column):
* Only US facilities above the threshold – a partial scope-1 proxy.
* Name matching is conservative; unmatched firms get scope1 = NaN, not 0.
"""

from __future__ import annotations

import re

import pandas as pd
import requests
from tqdm import tqdm

from esgx.config import END_YEAR, RAW_DIR, START_YEAR
from esgx.schema import validate

API = "https://data.epa.gov/efservice/{table}/year/{year}/rows/{a}:{b}/JSON"
PAGE = 10000

_LEGAL_TOKENS = {
    "INCORPORATED", "INC", "CORPORATION", "CORP", "COMPANY", "COMPANIES", "CO", "COS", "LLC",
    "LTD", "LIMITED", "PLC", "LP", "HOLDINGS", "HOLDING", "HLDGS", "GROUP", "SA", "NV", "AG",
}


def normalize_name(name: str) -> str:
    """Upper-case, strip punctuation, drop leading THE and trailing legal-form tokens."""
    s = str(name).upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\bL\s+L\s+C\b", "LLC", s)
    s = re.sub(r"\bL\s+P\b", "LP", s)
    toks = [t for t in s.split() if t]
    # canonical spellings so "PACKAGING CORP OF AMERICA" == "PACKAGING CORPORATION OF AMERICA"
    canon = {"CORPORATION": "CORP", "COMPANY": "CO", "COMPANIES": "COS", "INCORPORATED": "INC", "LIMITED": "LTD"}
    toks = [canon.get(t, t) for t in toks]
    while toks and toks[0] == "THE":
        toks = toks[1:]
    while toks and (toks[-1] in _LEGAL_TOKENS or toks[-1] == "THE"):
        toks = toks[:-1]
    return " ".join(toks)


def _fetch_table(table: str, year: int) -> pd.DataFrame:
    frames, a = [], 0
    while True:
        url = API.format(table=table, year=year, a=a, b=a + PAGE - 1)
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        frames.append(pd.DataFrame(chunk))
        if len(chunk) < PAGE:
            break
        a += PAGE
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _parse_parents(s: str) -> list[tuple[str, float]]:
    """'A CORP (60%); B LLC (40%)' -> [('A CORP', .6), ('B LLC', .4)]. No % -> equal split."""
    if not isinstance(s, str) or not s.strip():
        return []
    parts = [p.strip() for p in s.split(";") if p.strip()]
    out = []
    for p in parts:
        m = re.match(r"^(.*?)\s*\((\d+(?:\.\d+)?)%\)\s*$", p)
        if m:
            out.append((m.group(1).strip(), float(m.group(2)) / 100.0))
        else:
            out.append((p, None))
    n_missing = sum(1 for _, w in out if w is None)
    if n_missing:
        assigned = sum(w for _, w in out if w is not None)
        fill = max(0.0, 1.0 - assigned) / n_missing
        out = [(nm, fill if w is None else w) for nm, w in out]
    return out


def load_ghgrp_parent_emissions(refresh: bool = False, years: range | None = None) -> pd.DataFrame:
    """Parent-company × year total CO2e (t) from GHGRP facilities."""
    path = RAW_DIR / "ghgrp_parent_year.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    years = years or range(START_YEAR, END_YEAR + 1)
    rows = []
    for y in tqdm(list(years), desc="ghgrp", leave=False):
        fac = _fetch_table("pub_dim_facility", y)
        em = _fetch_table("pub_facts_sector_ghg_emission", y)
        if fac.empty or em.empty:
            continue
        em["co2e_emission"] = pd.to_numeric(em["co2e_emission"], errors="coerce")
        tot = em.groupby("facility_id")["co2e_emission"].sum()
        fac = fac.drop_duplicates("facility_id").set_index("facility_id")
        fac["co2e"] = tot.reindex(fac.index).fillna(0.0)
        for fid, r in fac.iterrows():
            for parent, w in _parse_parents(r.get("parent_company")):
                rows.append(
                    {
                        "year": int(y),
                        "parent_raw": parent,
                        "parent_norm": normalize_name(parent),
                        "co2e": float(r["co2e"]) * w,
                        "naics": str(r.get("naics_code", "")),
                        "facility_id": int(fid),
                    }
                )
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    return df


_MANUAL_ALIASES = {
    # universe normalised name -> GHGRP parent normalised name (only where obvious)
    "EXXONMOBIL": "EXXON MOBIL",
    "LYONDELLBASELL": "LYONDELLBASELL INDUSTRIES",
    "SEMPRA": "SEMPRA ENERGY",
    "WILLIAMS": "WILLIAMS COS",
    "AIR PRODUCTS": "AIR PRODUCTS AND CHEMICALS",
    "SMURFIT WESTROCK": "WESTROCK",
    "EXPAND ENERGY": "CHESAPEAKE ENERGY",
    "ALPHABET": "GOOGLE",
    "SOUTHERN": "SOUTHERN",
    "DOW": "DOW",
    "3M": "3M",
    "UNITED PARCEL SERVICE": "UNITED PARCEL SERVICE",
    "AMERICAN ELECTRIC POWER": "AMERICAN ELECTRIC POWER",
    "PPG INDUSTRIES": "PPG INDUSTRIES",
    "STEEL DYNAMICS": "STEEL DYNAMICS",
    "INTERNATIONAL PAPER": "INTERNATIONAL PAPER",
    "MARTIN MARIETTA MATERIALS": "MARTIN MARIETTA MATERIALS",
    "VULCAN MATERIALS": "VULCAN MATERIALS",
    "VULCAN MATERIALS COMPANY": "VULCAN MATERIALS",
    "TEXAS PACIFIC LAND": "TEXAS PACIFIC LAND",
    "CONSTELLATION ENERGY": "CONSTELLATION ENERGY",
    "VISTRA": "VISTRA",
    "NRG ENERGY": "NRG ENERGY",
    "AES": "AES",
    "BERKSHIRE HATHAWAY": "BERKSHIRE HATHAWAY ENERGY",
}


def match_to_universe(parent_year: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """Return `emissions` table (firm × year) with scope1 from GHGRP and a matched flag."""
    f = firms[["firm_id", "name"]].copy()
    f["norm"] = f["name"].map(normalize_name)
    f["norm_nospace"] = f["norm"].str.replace(" ", "", regex=False)

    p = parent_year.copy()
    p["parent_norm"] = p["parent_raw"].map(normalize_name)  # cache may predate normaliser changes
    p["norm_nospace"] = p["parent_norm"].str.replace(" ", "", regex=False)

    # 1) exact normalised match, 2) no-space match, 3) manual alias
    m1 = f.merge(p, left_on="norm", right_on="parent_norm", how="inner")
    m2 = f.merge(p, on="norm_nospace", how="inner", suffixes=("", "_p"))
    alias = f.assign(alias=f["norm"].map(_MANUAL_ALIASES)).dropna(subset=["alias"])
    m3 = alias.merge(p, left_on="alias", right_on="parent_norm", how="inner")

    # 4) prefix match: parent name starts with the firm name + a space, only for
    #    firm names with >= 2 tokens (avoids SOUTHERN -> SOUTHERN CALIFORNIA EDISON)
    multi = f[f["norm"].str.count(" ") >= 1]
    parents = p[["parent_norm"]].drop_duplicates()
    pairs = []
    for _, fr in multi.iterrows():
        hit = parents[parents["parent_norm"].str.startswith(fr["norm"] + " ")]
        for pn in hit["parent_norm"]:
            pairs.append({"firm_id": fr["firm_id"], "parent_norm": pn})
    m4 = pd.DataFrame(pairs, columns=["firm_id", "parent_norm"]).merge(p, on="parent_norm", how="inner")

    cols = ["firm_id", "year", "co2e", "facility_id"]
    m = pd.concat([m1[cols], m2[cols], m3[cols], m4[cols]], ignore_index=True).drop_duplicates(["firm_id", "year", "facility_id"])
    agg = m.groupby(["firm_id", "year"], as_index=False)["co2e"].sum()

    years = sorted(parent_year["year"].unique())
    grid = pd.MultiIndex.from_product([firms["firm_id"], years], names=["firm_id", "year"]).to_frame(index=False)
    out = grid.merge(agg, on=["firm_id", "year"], how="left")
    out["matched"] = out["co2e"].notna()
    out = out.rename(columns={"co2e": "scope1"})
    out["scope2"] = float("nan")
    out["scope3"] = float("nan")
    out["source"] = "EPA_GHGRP"
    out = out[["firm_id", "year", "scope1", "scope2", "scope3", "source", "matched"]]
    return validate(out, "emissions")
