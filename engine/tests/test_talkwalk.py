import pandas as pd

from esgx.ingest.text_filter import climate_passages
from esgx.measures.talkwalk import DryRunClient, aggregate_firm_year, score_document
from esgx.measures.text_measures import text_measures

TALKY = ("We are committed to net zero by 2050 and aim to lead the energy transition. " "We plan to reduce emissions and will target lower carbon intensity. ") * 20
WALKY = ("In 2023 we reduced scope 1 and 2 emissions by 12% versus 2019 and invested HK$3 billion in solar capacity, " "verified by an independent assurance provider. ") * 20


def _row(text, section="full_report", acc="https://www1.hkexnews.hk/x/0001"):
    return pd.Series({"firm_id": "0001.HK", "form": "esg_report", "filing_date": "2024-04-01", "period": "2023-12-31",
                      "accession": acc, "section": section, "text": text})


def test_climate_passages_filters():
    text = "Nothing here.\n\nWe discuss carbon emissions in detail here and more words to pass the length filter.\n\nUnrelated paragraph about office leases and headcount which is long enough."
    out, share = climate_passages(text, window=0)
    assert "carbon" in out and "office leases" not in out
    assert 0 < share < 1


def test_dry_run_scores_talk_vs_walk_direction(tmp_path, monkeypatch):
    import esgx.measures.talkwalk as tw

    monkeypatch.setattr(tw, "CACHE_DIR", tmp_path)
    c = DryRunClient()
    a = score_document(c, "Test Co", _row(TALKY, acc="https://x/a"), {})
    b = score_document(c, "Test Co", _row(WALKY, acc="https://x/b"), {})
    assert a["gap"] > b["gap"]
    assert a["talk"] > a["walk"] and b["walk"] > b["talk"]
    # cache hit on second call
    a2 = score_document(c, "Test Co", _row(TALKY, acc="https://x/a"), {})
    assert a2["talk"] == a["talk"]


def test_text_measures_direction():
    m_t, m_w = text_measures(TALKY), text_measures(WALKY)
    assert m_t["forward_looking_share"] > m_w["forward_looking_share"]
    assert m_w["realised_share"] > m_t["realised_share"]
    assert m_t["env_keyword_share"] > 0 and m_t["climate_similarity"] > 0


def test_aggregate_firm_year(tmp_path, monkeypatch):
    import esgx.measures.talkwalk as tw

    monkeypatch.setattr(tw, "CACHE_DIR", tmp_path)
    c = DryRunClient()
    rows = [score_document(c, "Test Co", _row(TALKY, acc="https://x/a"), {}), score_document(c, "Test Co", _row(WALKY, acc="https://x/b"), {})]
    fy = aggregate_firm_year(pd.DataFrame(rows))
    assert list(fy.columns[:2]) == ["firm_id", "year"] and fy.loc[0, "year"] == 2023 and fy.loc[0, "n_docs"] == 2
