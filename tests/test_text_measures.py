"""Directional tests for the dictionary text measures (no API needed)."""

from esgx.measures.text_measures import climate_similarity, env_sentiment, glossiness, text_measures

GLOSSY = """We are a leader in the energy transition and our renewable portfolio delivers strong progress.

Our carbon reduction programme achieved excellent results and our solar assets benefit customers.

Emission performance improved and we are a leading innovator in low-carbon hydrogen."""

RISKY = """Climate regulation creates adverse risk for our oil and gas operations and may impair assets.

Carbon taxes and litigation concerning emission liabilities could weaken our results.

Uncertain renewable mandates are a difficult concern and may negatively affect our coal business."""

NO_CLIMATE = """Net revenue grew and our retail stores delivered strong progress across all regions.

We opened new distribution centres and improved our excellent customer experience.

Operating margin benefited from leading cost discipline and innovation in logistics."""

FINANCE_PARA = "Our balance sheet is strong and the excellent results benefit shareholders with progress on every metric."


def test_glossiness_direction():
    g_glossy = glossiness(GLOSSY)["glossiness"]
    g_risky = glossiness(RISKY)["glossiness"]
    g_none = glossiness(NO_CLIMATE)["glossiness"]
    assert g_glossy > g_risky
    assert g_glossy > g_none
    assert g_none == 0.0


def test_gate_keeps_only_climate_segments():
    r = glossiness(GLOSSY)
    assert r["climate_share"] == 1.0
    assert r["gated_sentiment"] > 0
    assert glossiness(NO_CLIMATE)["climate_share"] == 0.0
    assert glossiness(RISKY)["gated_sentiment"] < 0


def test_non_climate_paragraph_dilutes_share_not_tone():
    base = glossiness(GLOSSY)
    mixed = glossiness(GLOSSY + "\n\n" + FINANCE_PARA)
    assert mixed["climate_share"] < base["climate_share"]
    assert mixed["gated_sentiment"] == base["gated_sentiment"]
    assert mixed["glossiness"] < base["glossiness"]


def test_sentence_fallback_when_no_paragraph_breaks():
    one_para = GLOSSY.replace("\n\n", " ")
    r = glossiness(one_para)
    assert r["climate_share"] > 0
    assert r["glossiness"] > 0


def test_empty_and_components_consistent():
    assert glossiness("") == {"climate_share": 0.0, "gated_sentiment": 0.0, "glossiness": 0.0}
    m = text_measures(GLOSSY)
    for k in ("climate_share", "gated_sentiment", "glossiness"):
        assert k in m
    assert climate_similarity(GLOSSY) > climate_similarity(NO_CLIMATE)
    assert env_sentiment(GLOSSY) > env_sentiment(RISKY)
