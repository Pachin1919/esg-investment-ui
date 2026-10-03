"""Source finders on synthetic data (no network, no API): link picking, news labelling, catalogue, agents."""

import pandas as pd

from esgx import llm
from esgx.agents import pipeline as pl
from esgx.agents.pipeline import Orchestrator, default_pipeline
from esgx.ingest import news_gdelt, sources, web_pages
from esgx.measures.talkwalk_clients import make_client
from pipeline.spec import AgentSpec
from pipeline.tools import llm_sources, storage
from pipeline.tools import sources as source_tools

HTML = """<html><body><nav><a href="/en/investors">Investors</a><a href="/en/about-us/overview">About Us</a>
<a href="https://other.com/x">Partner</a><a href="/en/sustainability">Sustainability</a><a href="#top">Top</a>
<a href="/zh/gongsi">公司簡介</a></nav></body></html>"""
ARTICLES = [
    {"title": "Alpha Power cuts emissions 12% as coal plant closes", "url": "https://n.com/1", "date": "2025-03-01", "publisher": "n.com", "language": "English"},
    {"title": "Markets wrap: stocks rise", "url": "https://n.com/2", "date": "2025-03-02", "publisher": "n.com", "language": "English"},
]


def test_provider_routing_and_default_model():
    assert llm.provider("kimi-k3") == "kimi" and llm.provider("claude-opus-5") == "anthropic"
    assert llm.key_env("kimi-k3") == "MOONSHOT_API_KEY"
    assert make_client().model == llm.PRIMARY_MODEL == "kimi-k3"


def test_page_links_same_site_only_and_about_heuristic():
    links = web_pages.page_links(HTML, "https://www.alpha.com/en")
    urls = [x["url"] for x in links]
    assert "https://other.com/x" not in urls and len(urls) == 4
    assert web_pages.heuristic_about(links)["url"].endswith("/about-us/overview")
    assert web_pages.heuristic_about([x for x in links if "about" not in x["url"]])["text"] == "公司簡介"
    assert web_pages.heuristic_about([{"text": "Careers", "url": "https://www.alpha.com/jobs"}]) is None


def test_news_query_and_heuristic_filter_keeps_the_relevant_article():
    assert news_gdelt.build_query("Alpha Power Holdings Limited").startswith('"Alpha Power Holdings" (')
    out = llm_sources.llm_filter_news("dry_run", AgentSpec(), "Alpha Power Holdings Limited", ARTICLES)
    assert out[0]["about_firm"] and out[0]["esg_related"] and out[0]["relevance"] > out[1]["relevance"]


def test_sources_frame_dedupes_and_validates():
    row = {"firm_id": "A", "source_type": "news", "title": "t", "url": "u", "date": "2025-01-01", "language": "", "publisher": "p", "found_by": "x", "relevance": 5.0, "note": ""}
    df = sources.merge_sources(sources.sources_frame([row, row]), sources.sources_frame([{**row, "url": "v"}]))
    assert list(df["url"]) == ["u", "v"] and list(df.columns) == sources.SOURCE_COLS


def test_finder_agents_dry_run_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(pl, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(storage, "_hk", lambda: pd.DataFrame({"firm_id": ["0001.HK"], "name": ["Alpha Power Holdings Limited"], "hkex_sid": [1], "stock_code": [1]}))
    monkeypatch.setattr(source_tools._src.hkexnews, "list_reports", lambda sid, start, kinds: [
        {"stock_code": 1, "doc_type": k, "filing_date": "2025-04-01", "fiscal_year": 2024, "title": f"2024 {k}", "url": f"https://hk/{k}.pdf", "size": ""}
        for k in kinds])
    monkeypatch.setattr(source_tools._web, "company_website", lambda t: "https://www.alpha.com/en")
    monkeypatch.setattr(source_tools._web, "fetch_html", lambda url: HTML)
    monkeypatch.setattr(source_tools._news, "search_news", lambda *a, **k: ARTICLES)
    spec = default_pipeline()
    spec.universe = "hk"
    for s in spec.stages:
        s.enabled = s.kind.startswith("find_") or s.kind == "aggregate"
    run = Orchestrator().start(spec, ["0001.HK", "ZZZ"], "dry_run", blocking=True)
    assert run.status == "done", run.error
    src = pd.DataFrame(run.results["sources"])
    counts = src["source_type"].value_counts().to_dict()
    assert counts == {"annual_report": 1, "esg_report": 1, "interim_report": 1, "quarterly_report": 1, "about_page": 1, "news": 1}
    assert src[src["source_type"] == "news"]["url"].iloc[0] == "https://n.com/1"
    assert (run.dir / "sources.csv").exists()
