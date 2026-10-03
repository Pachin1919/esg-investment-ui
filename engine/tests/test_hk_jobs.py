import pandas as pd


def test_shards_partition_firms_and_parts_merge(tmp_path, monkeypatch):
    from esgx.ingest import hk_jobs as jobs
    from esgx.ingest import hk_stream as st

    monkeypatch.setattr(jobs, "PROCESSED_DIR", tmp_path)
    firms = pd.DataFrame({"firm_id": [f"{i:04d}.HK" for i in range(1, 11)], "stock_code": range(1, 11), "hkex_sid": range(101, 111)})
    picked = [set(jobs.take_shard(firms, (i, 3))["firm_id"]) for i in range(3)]
    assert set().union(*picked) == set(firms["firm_id"]) and sum(map(len, picked)) == 10  # disjoint and complete
    assert jobs.shard_from_env("2/5") == (2, 5) and jobs.shard_from_env() == (0, 1)
    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "7")
    monkeypatch.setenv("CLOUD_RUN_TASK_COUNT", "20")
    assert jobs.shard_from_env() == (7, 20)

    # each shard streams its own firms into its own part files; a rerun skips what any shard stored
    listed = {sid: [{"stock_code": sid - 100, "doc_type": "esg_report", "filing_date": "2025-04-01", "fiscal_year": 2024,
                     "title": "ESG Report", "url": f"https://x/{sid}.pdf", "size": "1MB"}] for sid in range(101, 111)}
    calls = []
    monkeypatch.setattr(jobs, "list_reports", lambda sid, start: listed[sid])

    def fake_process(firm_id, rep):
        calls.append(rep["url"])
        if rep["url"].endswith("/103.pdf"):
            raise ValueError("broken pdf")
        return {"firm_id": firm_id, **rep, "n_pages": 3}, [{"firm_id": firm_id, "url": rep["url"], "doc_type": "esg_report", "fiscal_year": 2024, "category": "ghg", "page": 2, "score": 5, "text": "Scope 1 10 tCO2e"}]

    monkeypatch.setattr(st, "process_report", fake_process)
    for i in range(3):
        jobs.documents(firms, "2022-01-01", shard=(i, 3), workers=2)
    assert len(list((tmp_path / "hk_reports").glob("part-*.parquet"))) == 3
    allr = jobs.read_parts("hk_reports")
    assert len(allr) == 9 and allr["url"].is_unique  # ten firms, one failed
    assert "broken pdf" in (tmp_path / "hk_failures" / "part-0002-of-0003.jsonl").read_text()
    n = len(calls)
    jobs.documents(firms, "2022-01-01", shard=(0, 1), workers=2)  # different sharding, same store: only the failed report is retried
    assert len(calls) == n + 1
    docs, pages = jobs.emission_docs(firms, (0, 2))
    assert set(docs["firm_id"]) <= set(jobs.take_shard(firms, (0, 2))["firm_id"]) and len(pages) == 9
    assert st.cache_key({"url": "https://x/101.pdf", "stock_code": 1}) == "https://x/101.pdf"
