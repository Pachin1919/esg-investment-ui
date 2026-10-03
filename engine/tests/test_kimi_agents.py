"""Kimi agents on synthetic inputs (no network, no API key): report typing, link picking, news labelling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kimi-agents"))

from kimi_agents import about_page, gdelt, news, reports, web
from kimi_agents.sources import SOURCE_COLS, sources_frame

HTML = """<html><body><a href="/en/investors">Investors</a><a href="/en/about-us/overview">About Us</a>
<a href="https://other.com/x">Partner</a><a href="/en/sustainability">Sustainability</a><a href="#top">Top</a>
<a href="/zh/gongsi">公司簡介</a></body></html>"""
TITLES = [
    {"TITLE": "2024 Annual Report", "DATE_TIME": "10/04/2025 16:30", "FILE_LINK": "/a.pdf", "FILE_TYPE": "PDF", "STOCK_CODE": "00883<br/>80883"},
    {"TITLE": "2025 Interim Report", "DATE_TIME": "10/09/2025 16:30", "FILE_LINK": "/b.pdf", "FILE_TYPE": "PDF", "STOCK_CODE": "00883"},
    {"TITLE": "2025 Third Quarterly Report", "DATE_TIME": "30/10/2025 16:30", "FILE_LINK": "/c.pdf", "FILE_TYPE": "PDF", "STOCK_CODE": "00883"},
    {"TITLE": "Environmental, Social and Governance Report 2024", "DATE_TIME": "10/04/2025 16:31", "FILE_LINK": "/d.pdf", "FILE_TYPE": "PDF", "STOCK_CODE": "00883"},
    {"TITLE": "Notice of Annual General Meeting", "DATE_TIME": "11/04/2025 16:30", "FILE_LINK": "/e.pdf", "FILE_TYPE": "PDF", "STOCK_CODE": "00883"},
]
ARTICLES = [
    {"title": "Alpha Power cuts emissions 12% as coal plant closes", "url": "https://n.com/1", "date": "2025-03-01", "publisher": "n.com", "language": "English"},
    {"title": "Markets wrap: stocks rise", "url": "https://n.com/2", "date": "2025-03-02", "publisher": "n.com", "language": "English"},
]


def test_reports_are_typed_from_titles_and_dated_by_filing():
    rows = reports.run("0883.HK", 1, rows=TITLES)
    assert [r["source_type"] for r in rows] == ["annual_report", "interim_report", "quarterly_report", "esg_report"]
    assert rows[0]["date"] == "2025-04-10" and rows[0]["note"] == "FY2024" and rows[0]["url"].endswith("/a.pdf")


def test_about_page_picks_from_same_site_links_only():
    links = web.page_links(HTML, "https://www.alpha.com/en")
    assert "https://other.com/x" not in [x["url"] for x in links] and len(links) == 4
    assert about_page.pick("Alpha", links, live=False)["url"].endswith("/about-us/overview")
    assert about_page.pick("Alpha", [x for x in links if "about" not in x["url"]], live=False)["title"] == "公司簡介"
    assert about_page.pick("Alpha", [], live=False)["url"] is None


def test_news_keeps_the_article_about_the_firm_and_esg():
    assert gdelt.build_query("Alpha Power Holdings Limited").startswith('"Alpha Power Holdings" (')
    rows, msg = news.run("0001.HK", "Alpha Power Holdings Limited", "2025-01-01", live=False, articles=ARTICLES)
    assert [r["url"] for r in rows] == ["https://n.com/1"] and msg == "2 hits, 1 kept"
    assert rows[0]["source_type"] == "news" and rows[0]["date"] == "2025-03-01"


def test_sources_frame_has_all_columns_and_drops_duplicates():
    rows = reports.run("0883.HK", 1, rows=TITLES)
    df = sources_frame(rows + rows[:1])
    assert list(df.columns) == SOURCE_COLS and len(df) == 4
