"""Taiwan: listed-company universe and ESG hard data from the TWSE and TPEx OpenAPIs (free, no key).

The Taiwan Stock Exchange (main board) and the Taipei Exchange (TPEx, OTC) publish the ESG
figures every listed company files on the ESG disclosure platform as open data, one dataset per
topic (https://openapi.twse.com.tw, https://www.tpex.org.tw/openapi; TPEx dataset names end in
`_O` and its company basics use English keys):

  t187ap03_L     company basics (code, names, industry code, paid-in capital)
  t187ap46_L_1   GHG: scope 1 / 2 / 3 in tCO2e, data boundary, third-party verification
  t187ap46_L_2   energy: renewable share of total energy
  t187ap46_L_3   water: consumption in tonnes
  t187ap46_L_4   waste: hazardous / non-hazardous tonnes
  t187ap05_L     monthly revenue incl. cumulative revenue this year and last year (NT$ thousand)

This is a registry-like source: figures are structured, cover the whole market (about 1 080 TWSE
and 890 TPEx firms; `firm_id` is the code plus `.TW` / `.TWO` as in yfinance, `exchange` says which)
and carry a verification flag, so no LLM extraction is needed. Limits: the API serves the latest
reporting year only (no history, so no trend), figures are self-reported, and the boundary is
either the parent or the consolidated group (kept in `boundary`).

Revenue: the API has no full-year income statement for the reporting year. Last year's cumulative
revenue through the latest published month is annualised (x 12 / month) as the intensity
denominator and flagged in `revenue_basis`; within-industry ranks are robust to the seasonality
error, absolute intensities are approximate. TWD converted at a fixed 32 per USD (`fx_note`).
"""

from __future__ import annotations

import pandas as pd
import requests

from esgx.config import PROCESSED_DIR, RAW_DIR
from esgx.schema import validate

EXCHANGES = {  # api base, dataset names, yfinance suffix, keys of the company-basics table
    "TWSE": {"api": "https://openapi.twse.com.tw/v1/opendata/", "basics": "t187ap03_L", "esg": "t187ap46_L_", "revenue": "t187ap05_L", "suffix": ".TW",
             "keys": {"code": "公司代號", "abbr": "公司簡稱", "en": "英文簡稱", "industry": "產業別", "capital": "實收資本額"}},
    "TPEx": {"api": "https://www.tpex.org.tw/openapi/v1/", "basics": "mopsfin_t187ap03_O", "esg": "t187ap46_O_", "revenue": "mopsfin_t187ap05_O", "suffix": ".TWO",
             "keys": {"code": "SecuritiesCompanyCode", "abbr": "CompanyAbbreviation", "en": "Symbol", "industry": "SecuritiesIndustryCode", "capital": "Paidin.Capital.NTDollars"}},
}
_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)", "Accept": "application/json"}
TWD_PER_USD = 32.0
INDUSTRY = {
    "01": "Cement", "02": "Food", "03": "Plastics", "04": "Textiles", "05": "Electric Machinery", "06": "Electrical and Cable",
    "08": "Glass and Ceramics", "09": "Paper and Pulp", "10": "Iron and Steel", "11": "Rubber", "12": "Automobile",
    "14": "Building Material and Construction", "15": "Shipping and Transportation", "16": "Tourism", "17": "Finance and Insurance",
    "18": "Trading and Consumer Goods", "20": "Other", "21": "Chemical", "22": "Biotechnology and Medical Care",
    "23": "Oil, Gas and Electricity", "24": "Semiconductor", "25": "Computer and Peripheral Equipment", "26": "Optoelectronic",
    "27": "Communications and Internet", "28": "Electronic Parts and Components", "29": "Electronic Products Distribution",
    "30": "Information Service", "31": "Other Electronic", "35": "Green Energy and Environmental Services",
    "32": "Cultural and Creative", "33": "Agricultural Technology", "34": "E-commerce",
    "36": "Digital and Cloud Services", "37": "Sports and Leisure", "38": "Household", "91": "Depositary Receipts",
}


def _get(exchange: str, dataset: str) -> list[dict]:
    r = requests.get(EXCHANGES[exchange]["api"] + dataset, headers=_HEADERS, timeout=60)
    r.raise_for_status()
    return [{k.strip(): v for k, v in row.items()} for row in r.json()]


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.rstrip("%"), errors="coerce")


def _firm_id(code: pd.Series, exchange: str) -> pd.Series:
    return code.astype(str).str.strip() + EXCHANGES[exchange]["suffix"]


def _each_exchange(build) -> pd.DataFrame:
    return pd.concat([build(ex).assign(exchange=ex) for ex in EXCHANGES], ignore_index=True)


def load_universe_tw(refresh: bool = False) -> pd.DataFrame:
    """All TWSE- and TPEx-listed companies in the `firms` schema; `sector` is the exchange industry in English."""
    path = RAW_DIR / "universe_twse.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    def build(ex: str) -> pd.DataFrame:
        b, k = pd.DataFrame(_get(ex, EXCHANGES[ex]["basics"])), EXCHANGES[ex]["keys"]
        en = b[k["en"]].astype(str).str.replace("\u3000", " ").str.strip() if k["en"] in b else pd.Series("", index=b.index)
        return pd.DataFrame({
            "firm_id": _firm_id(b[k["code"]], ex), "name": en.where(en != "", b[k["abbr"]]), "name_zh": b[k["abbr"]],
            "sector": b[k["industry"]].map(INDUSTRY).fillna("Other"), "industry": b[k["industry"]], "cik": pd.NA, "country": "TW",
            "paid_in_capital_twd": _num(b[k["capital"]]),
        })

    df = _each_exchange(build)
    validate(df, "firms").to_parquet(path, index=False)
    return df


def load_emissions_tw(refresh: bool = False) -> pd.DataFrame:
    """Firm × reporting year in the `emissions` schema plus verification flags, boundary and the
    energy / water / waste key figures. Scope figures in tCO2e as filed."""
    path = PROCESSED_DIR / "emissions_tw.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    extra = {"2": {"使用率(再生能源/總能源)": "renewable_share_pct"}, "3": {"用水量(公噸)": "water_tonnes"},
             "4": {"總重量(有害+非有害)-數據(公噸)": "waste_tonnes", "有害廢棄物量-數據(公噸)": "hazardous_waste_tonnes"}}

    def build(ex: str) -> pd.DataFrame:
        g = pd.DataFrame(_get(ex, EXCHANGES[ex]["esg"] + "1"))
        df = pd.DataFrame({
            "firm_id": _firm_id(g["公司代號"], ex), "year": _num(g["報告年度"]).astype(int) + 1911,  # ROC calendar
            "scope1": _num(g["範疇一排放量(噸CO2e)"]), "scope2": _num(g["範疇二排放量(噸CO2e)"]), "scope3": _num(g["範疇三排放量(噸CO2e)"]),
            "source": f"{ex.lower()}_esg_openapi", "scope1_verified": g["範疇一取得驗證"].eq("是"), "scope2_verified": g["範疇二取得驗證"].eq("是"),
            "boundary": g["範疇一資料邊界"],
        })
        for n, cols in extra.items():
            t = pd.DataFrame(_get(ex, EXCHANGES[ex]["esg"] + n))
            t = pd.DataFrame({"firm_id": _firm_id(t["公司代號"], ex), **{new: _num(t[old]) for old, new in cols.items() if old in t}})
            df = df.merge(t.drop_duplicates("firm_id"), on="firm_id", how="left")
        return df

    df = _each_exchange(build)
    df["matched"] = df["scope1"].notna() | df["scope2"].notna()
    df["verified"] = df["scope1_verified"] & df["scope2_verified"]
    validate(df, "emissions").to_parquet(path, index=False)
    return df


def load_fundamentals_tw(refresh: bool = False) -> pd.DataFrame:
    """Firm × year revenue in USD millions: last year's cumulative monthly revenue, annualised."""
    path = RAW_DIR / "fundamentals_twse.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    def build(ex: str) -> pd.DataFrame:
        m = pd.DataFrame(_get(ex, EXCHANGES[ex]["revenue"]))
        ym = _num(m["資料年月"]).astype(int)  # ROC yyyMM
        month = ym % 100
        cum_last_year = _num(m["累計營業收入-去年累計營收"])  # NT$ thousand
        return pd.DataFrame({
            "firm_id": _firm_id(m["公司代號"], ex), "year": ym // 100 + 1911 - 1,
            "revenue": cum_last_year * 12 / month * 1000 / TWD_PER_USD / 1e6, "book_equity": float("nan"), "currency": "TWD",
            "fx_note": f"fixed {TWD_PER_USD:.0f} TWD/USD, approximate",
            "revenue_basis": "Jan-" + month.astype(str).str.zfill(2) + " cumulative, annualised",
        })

    df = _each_exchange(build)
    validate(df, "fundamentals").to_parquet(path, index=False)
    return df
