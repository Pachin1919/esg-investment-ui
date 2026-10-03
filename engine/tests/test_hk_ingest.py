"""Unit tests for the Hong Kong ingest path (no network, no API)."""

from __future__ import annotations

import pandas as pd

from esgx.ingest.emissions_hk import (
    EmissionsExtraction,
    Evidence,
    YearRow,
    candidate_pages,
    consolidate,
    rows_from_extraction,
)
from esgx.ingest.factors import REGIONS
from esgx.ingest.hkexnews import classify_title, fiscal_year_from_title
from esgx.ingest.universe_hk import code_from_ticker, yf_symbol


def test_ticker_parsing():
    assert code_from_ticker("SEHK: 5") == 5
    assert code_from_ticker("SEHK:0700") == 700
    assert yf_symbol(5) == "0005.HK"
    assert yf_symbol(9988) == "9988.HK"


def test_factor_regions_have_both_files():
    for ff5, mom in REGIONS.values():
        assert ff5.endswith("_CSV.zip") and mom.endswith("_CSV.zip")


def test_title_classification():
    assert classify_title("2024 Annual Report") == "annual_report"
    assert classify_title("Environmental, Social and Governance Report 2024") == "esg_report"
    assert classify_title("Sustainability Report 2023") == "esg_report"
    assert classify_title("2024 Interim Report") == "interim_report"
    assert classify_title("2024 Third Quarterly Report") == "quarterly_report"
    assert classify_title("Annual Report 2023/24 (with linked Sustainability Report)") == "annual_report"


def test_fiscal_year_parsing():
    assert fiscal_year_from_title("2024 Annual Report", "2025-03-11") == 2024
    assert fiscal_year_from_title("Annual Report 2023/24", "2024-07-01") == 2024
    assert fiscal_year_from_title("ESG Report", "2025-04-20") == 2024


def test_candidate_pages_rank_scope_tables_first():
    pages = ["Chairman's statement about growth."] * 10
    pages[4] = "GHG emissions: Scope 1 12,345 tCO2e; Scope 2 67,890 tCO2e (location-based)"
    pages[7] = "Our climate strategy mentions greenhouse gas reduction."
    chosen = candidate_pages(pages, top_k=2)
    assert [i for i, _ in chosen] == [5, 8]  # page order, 1-based
    assert "Scope 1 12,345" in chosen[0][1]


def _doc(**kw) -> pd.Series:
    base = {"firm_id": "0002.HK", "doc_type": "esg_report", "fiscal_year": 2024, "url": "u", "title": "t", "path": "p"}
    return pd.Series({**base, **kw})


def test_rows_and_consolidation_prefer_latest_report():
    ex_new = EmissionsExtraction(found=True, confidence=0.9, third_party_assured=True,
                                 series=[YearRow(fiscal_year=2024, scope1_tco2e=100.0, scope2_tco2e=50.0, scope2_basis="location"),
                                         YearRow(fiscal_year=2023, scope1_tco2e=110.0, scope2_tco2e=55.0, scope2_basis="location")],
                                 evidence=[Evidence(page=12, quote="Scope 1 100 tCO2e")])
    ex_old = EmissionsExtraction(found=True, confidence=0.9, series=[YearRow(fiscal_year=2023, scope1_tco2e=120.0, scope2_tco2e=60.0)],
                                 evidence=[Evidence(page=3, quote="Scope 1 120 tCO2e")])
    rows = pd.DataFrame(rows_from_extraction(_doc(), ex_new) + rows_from_extraction(_doc(fiscal_year=2023), ex_old))
    assert len(rows) == 3
    out = consolidate(rows)
    assert len(out) == 2
    # 2023 comes from the 2024 report (restated value 110), not the 2023 report
    assert out.set_index("year").loc[2023, "scope1"] == 110.0
    assert out.set_index("year").loc[2024, "verified"]
    assert {"firm_id", "year", "scope1", "scope2", "scope3", "source", "matched"} <= set(out.columns)


def test_rows_skip_years_without_figures():
    ex = EmissionsExtraction(found=False, confidence=0.2, series=[YearRow(fiscal_year=2024)])
    assert rows_from_extraction(_doc(), ex) == []


def test_kpi_pages_keep_only_pages_with_esg_figures():
    from esgx.ingest.hk_stream import chosen_pages, kpi_pages, pick_reports

    pages = [
        "Chairman's statement. We delivered solid growth for our shareholders this year.",
        "Scope 1 emissions 12,345 tCO2e; Scope 2 emissions 6,789 tCO2e. Total GHG emissions 19,134 tonnes CO2e.",
        "Electricity consumption 4,200 MWh. Energy intensity 0.8 GJ per unit.",
        "Water consumption 15,000 m3. Hazardous waste generated 12 tonnes.",
    ]
    kept = pd.DataFrame(kpi_pages(pages))
    assert set(kept["page"]) == {2, 3, 4}  # narrative page 1 is dropped
    assert kept[kept["category"] == "ghg"]["page"].tolist() == [2]
    assert kept[kept["category"] == "energy"]["page"].tolist() == [3]
    assert set(kept[kept["category"] == "water"]["page"]) == {4} and set(kept[kept["category"] == "waste"]["page"]) == {4}
    kept["url"] = "u"
    assert chosen_pages(kept, "u", "ghg") == [(2, pages[1])]
    reps = pd.DataFrame({"firm_id": ["A", "A"], "fiscal_year": [2024, 2024], "doc_type": ["annual_report", "esg_report"], "filing_date": ["2025-04-01", "2025-04-01"]})
    assert pick_reports(reps)["doc_type"].tolist() == ["esg_report"]


def test_twse_esg_tables_parse_into_schema(tmp_path, monkeypatch):
    from esgx.ingest import twse_esg as tw

    payload = {
        "t187ap03_L": [{"公司代號": "2330", "公司簡稱": "台積電", "英文簡稱": "TSMC", "產業別": "24", "實收資本額": "259303804580"}],
        "t187ap46_L_1": [{"報告年度": "114", "公司代號": "2330", "範疇一排放量(噸CO2e)": "2196516.0000", "範疇一資料邊界": "合併", "範疇一取得驗證": "是",
                          "範疇二排放量(噸CO2e)": "11130571.0000", "範疇二取得驗證": "是", "範疇三排放量(噸CO2e)": ""}],
        "t187ap46_L_2": [{"公司代號": "2330", "使用率(再生能源/總能源)": "20.1000%"}],
        "t187ap46_L_3": [{"公司代號": "2330", "用水量(公噸)": "127121673.0000"}],
        "t187ap46_L_4": [{"公司代號": "2330", "總重量(有害+非有害)-數據(公噸)": "100.0", "有害廢棄物量-數據(公噸) ": "40.0"}],
        "t187ap05_L": [{"資料年月": "11508", "公司代號": "2330", "累計營業收入-去年累計營收": "2400000000"}],
    }
    monkeypatch.setattr(tw, "EXCHANGES", {"TWSE": tw.EXCHANGES["TWSE"]})
    monkeypatch.setattr(tw, "_get", lambda ex, d: [{k.strip(): v for k, v in r.items()} for r in payload[d]])
    monkeypatch.setattr(tw, "RAW_DIR", tmp_path)
    monkeypatch.setattr(tw, "PROCESSED_DIR", tmp_path)
    f, e, r = tw.load_universe_tw(), tw.load_emissions_tw(), tw.load_fundamentals_tw()
    assert f.loc[0, "firm_id"] == "2330.TW" and f.loc[0, "sector"] == "Semiconductor" and f.loc[0, "exchange"] == "TWSE"
    assert e.loc[0, "year"] == 2025 and e.loc[0, "scope1"] == 2196516 and bool(e.loc[0, "verified"]) and pd.isna(e.loc[0, "scope3"])
    assert e.loc[0, "renewable_share_pct"] == 20.1 and e.loc[0, "hazardous_waste_tonnes"] == 40
    # Jan-Aug 2025 cumulative NT$ 2.4 trillion -> annualised, USD millions at 32 TWD/USD
    assert r.loc[0, "year"] == 2025 and abs(r.loc[0, "revenue"] - 2.4e9 * 1.5 * 1000 / 32 / 1e6) < 1e-6


def test_list_reports_handles_dual_counter_stock_codes(monkeypatch):
    import json as _json

    from esgx.ingest import hkexnews as hx

    class R:
        def raise_for_status(self): ...
        def json(self):
            return {"result": _json.dumps([{"STOCK_CODE": "00016<br/>80016", "TITLE": "2024 Sustainability Report", "DATE_TIME": "30/10/2024 16:30",
                                            "FILE_LINK": "/listedco/x.pdf", "FILE_TYPE": "PDF", "FILE_INFO": "5MB"}])}

    monkeypatch.setattr(hx.requests, "get", lambda *a, **k: R())
    monkeypatch.setattr(hx.time, "sleep", lambda s: None)
    reps = hx.list_reports(16)
    assert reps[0]["stock_code"] == 16 and reps[0]["doc_type"] == "esg_report"


def test_hsci_proxy_keeps_vcm_eligible_hkd_equities(monkeypatch):
    import io as _io

    from esgx.ingest import universe_hk as u

    rows = [["List of Securities"] + [None] * 5, ["Updated"] + [None] * 5,
            ["Stock Code", "Name of Securities", "Category", "VCM Eligible", "Trading Currency", "Sub-Category"],
            ["00001", "CKH HOLDINGS", "Equity", "Y", "HKD", "Main Board"], ["80016", "SHK PPT-R", "Equity", "Y", "CNY", "Main Board"],
            ["00823", "LINK REIT", "Real Estate Investment Trusts", "Y", "HKD", "REIT"], ["08001", "SMALL CO", "Equity", " ", "HKD", "GEM"],
            ["12345", "SOME WARRANT", "Derivative Warrants", " ", "HKD", "DW"]]
    buf = _io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, header=False, index=False)

    class R:
        content = buf.getvalue()

    monkeypatch.setattr(u.requests, "get", lambda *a, **k: R())
    out = u._hkex_vcm_equities()
    assert out["stock_code"].tolist() == [1, 823] and out["name"].tolist() == ["CKH HOLDINGS", "LINK REIT"]

