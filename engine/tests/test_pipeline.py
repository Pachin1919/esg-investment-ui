"""Orchestrator tests in dry-run mode on synthetic HKEX documents (no network, no API)."""

import pandas as pd
import pytest

from esgx.agents import pipeline as pl
from esgx.agents.method import method_snapshot
from esgx.agents.pipeline import (
    AgentSpec,
    Orchestrator,
    PipelineSpec,
    default_pipeline,
    estimate_cost,
)
from esgx.ingest import hk_documents
from esgx.measures import hard_data as hd
from esgx.measures import talkwalk as tw
from pipeline.tools import TOOLS, ToolBox, storage

DOC = """Climate change and emission targets. We reduced scope 1 and 2 emissions by 12 % since 2019 and invested HK$15 billion
in renewable generation. We aim to reach net zero by 2050 and will target further reductions. """ * 20


def _docs():
    return pd.DataFrame([
        {"firm_id": "0001.HK", "form": "esg_report", "filing_date": "2024-04-01", "period": "2023-12-31",
         "accession": "https://www1.hkexnews.hk/x/a1", "section": "full_report", "text": DOC, "title": "2023 ESG Report", "fiscal_year": 2023},
        {"firm_id": "0001.HK", "form": "esg_report", "filing_date": "2023-04-01", "period": "2022-12-31",
         "accession": "https://www1.hkexnews.hk/x/a0", "section": "full_report", "text": DOC, "title": "2022 ESG Report", "fiscal_year": 2022},
    ])


@pytest.fixture
def fake_sources(monkeypatch, tmp_path):
    monkeypatch.setattr(pl, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(storage, "_hk", lambda: pd.DataFrame({"firm_id": ["0001.HK"], "stock_code": [1], "hkex_sid": [123], "name": ["Alpha Holdings"]}))
    monkeypatch.setattr(hk_documents, "report_documents", lambda *a, **k: _docs())
    monkeypatch.setattr(hd, "hard_data_for", lambda f, y, market="hk": {"scope12_tCO2e_2022": 100, "scope12_tCO2e_2023": 110, "scope12_change_pct": 10.0})
    monkeypatch.setattr(tw, "CACHE_DIR", tmp_path / "cache")


def test_default_pipeline_is_valid_and_ordered():
    spec = default_pipeline()
    kinds = [s.kind for s in spec.stages]
    assert kinds[:3] == ["find_reports", "find_about_page", "find_news"] and kinds[3] == "collect_documents" and kinds[-1] == "aggregate"
    assert not any(s.enabled for s in spec.stages[:3])  # source finders are opt-in
    assert any(s.agent for s in spec.stages)
    assert spec.universe == "hk"
    assert PipelineSpec.model_validate(spec.model_dump()) == spec


def test_dry_run_end_to_end(fake_sources):
    run = Orchestrator().start(default_pipeline(), ["0001.HK", "9999.HK"], "dry_run", blocking=True)
    assert run.status == "done", run.error
    assert all(s["status"] in ("done", "skipped") for s in run.stages.values())
    fy = run.results["firm_years"]
    assert {r["year"] for r in fy} == {2022, 2023}
    assert all(0 <= r["talk"] <= 10 and 0 <= r["walk"] <= 10 for r in fy)
    docs = run.results["documents"]
    assert "glossiness" in docs[0]  # dictionary stage merged in
    memos = run.results["memos"]
    assert len(memos) == 2 and any("emissions rising" in f for m in memos for f in m["flags"])
    assert (run.dir / "firm_year.csv").exists() and (run.dir / "run.json").exists()
    assert any("not in universe" in line["msg"] for line in run.log)


def test_disabled_stage_is_skipped_and_agent_variant_changes_cache_key(fake_sources, tmp_path):
    spec = default_pipeline()
    for s in spec.stages:
        if s.kind == "review":
            s.enabled = False
        if s.kind == "score_talkwalk":
            s.agent = AgentSpec(name="Strict", role_prompt="Be twice as strict on walk.")
    run = Orchestrator().start(spec, ["0001.HK"], "dry_run", blocking=True)
    assert run.status == "done", run.error
    assert run.stages["review"]["status"] == "skipped"
    assert run.results["memos"] == []
    base = tw._cache_key("a1", "full_report", "dry-run", DOC)
    variant = tw._cache_key("a1", "full_report", "dry-run", DOC, tw.SYSTEM_PROMPT + "\nextra")
    assert base != variant


def test_weights_change_aggregate(fake_sources):
    spec = default_pipeline()
    for s in spec.stages:
        if s.kind == "score_talkwalk":
            s.params["walk_weights"] = {"realised_reductions": 1.0}
    run = Orchestrator().start(spec, ["0001.HK"], "dry_run", blocking=True)
    docs = run.results["documents"]
    assert all(abs(d["walk"] - d["walk_realised_reductions"]) < 1e-9 for d in docs if not d["skipped"])


def test_toolbox_enforces_allowed_tools():
    box = ToolBox(("text_measures",))
    assert box.text_measures("carbon emission reduced")["n_env_hits"] >= 1
    with pytest.raises(PermissionError):
        getattr(box, "llm_score_section")  # noqa: B009
    with pytest.raises(KeyError):
        ToolBox(("no_such_tool",))
    assert {t.kind for t in TOOLS.values()} <= {"api", "scrape", "compute", "llm", "storage"}
    assert all(t.description for t in TOOLS.values())


def test_agents_only_use_registered_tools_and_llm_agents_have_no_write_tools():
    from pipeline.agents import AGENTS

    for a in AGENTS.values():
        assert set(a.tools) <= set(TOOLS)
        if a.llm:
            assert not any(TOOLS[t].name.startswith(("write_", "publish_")) for t in a.tools)
    assert [a.kind for a in AGENTS.values()] == [s.kind for s in default_pipeline().stages]


def test_estimate_and_snapshot():
    est = estimate_cost(default_pipeline(), n_sections=12, n_firm_years=4)
    assert est["scorer_usd"] == pytest.approx(0.96) and est["total_usd"] == pytest.approx(0.96 + 0.12)
    snap = method_snapshot()
    assert snap["rubric_version"] == tw.RUBRIC_VERSION and sum(snap["talk_weights"].values()) == pytest.approx(1.0)
