import pandas as pd

from esgx.portfolio.screen import PreferenceFilter, apply_filter, screen_keywords, screen_universe


def _universe():
    rows = [
        ("0001.HK", "Alpha Bank", "Financials", "Banks", "Hong Kong"),
        ("0002.HK", "Beta Power", "Utilities", "Electric Utilities", "Hong Kong"),
        ("0003.HK", "Gamma Gas", "Utilities", "Gas Utilities", "Hong Kong"),
        ("0005.HK", "Delta Holdings", "Industrials", "Industrial Conglomerates", "China"),
        ("0006.HK", "Epsilon Tech", "Information Technology", "Software", "China"),
        ("0007.HK", "Zeta Oil", "Energy", "Oil & Gas", "China"),
    ]
    return pd.DataFrame(rows, columns=["firm_id", "name", "sector", "industry", "country"])


def _mktcap():  # terciles: small 0003/0006, mid 0005/0007, large 0002/0001
    return pd.Series({"0001.HK": 900.0, "0002.HK": 800.0, "0003.HK": 100.0,
                      "0005.HK": 500.0, "0006.HK": 200.0, "0007.HK": 700.0})


def _spec(**kw):
    return PreferenceFilter(**kw)


def test_apply_filter_include_exclude():
    uni, mc = _universe(), _mktcap()
    assert apply_filter(uni, _spec(include_sectors=["Utilities"]), mc) == ["0002.HK", "0003.HK"]
    assert apply_filter(uni, _spec(exclude_sectors=["Energy"]), mc) == \
        ["0001.HK", "0002.HK", "0003.HK", "0005.HK", "0006.HK"]
    # include and exclude combine across dimensions; exclusion wins
    got = apply_filter(uni, _spec(include_sectors=["Utilities", "Energy"], exclude_industries=["Oil & Gas"]), mc)
    assert got == ["0002.HK", "0003.HK"]
    assert apply_filter(uni, _spec(countries=["China"]), mc) == ["0005.HK", "0006.HK", "0007.HK"]
    assert apply_filter(uni, _spec(keywords=["tech"]), mc) == ["0006.HK"]


def test_apply_filter_size_terciles():
    uni, mc = _universe(), _mktcap()
    assert apply_filter(uni, _spec(size=["large"]), mc) == ["0001.HK", "0002.HK"]
    assert apply_filter(uni, _spec(size=["small"]), mc) == ["0003.HK", "0006.HK"]
    assert apply_filter(uni, _spec(size=["large", "mid"]), mc) == ["0001.HK", "0002.HK", "0005.HK", "0007.HK"]
    assert apply_filter(uni, _spec(include_sectors=["Financials"], size=["large"]), mc) == ["0001.HK"]


def test_screen_keywords_reads_size_sector_and_negation():
    spec = screen_keywords("large cap banks", _universe())
    assert spec.size == ["large"] and spec.include_industries == ["Banks"]
    assert apply_filter(_universe(), spec, _mktcap()) == ["0001.HK"]
    spec = screen_keywords("utilities but no gas", _universe())
    assert spec.include_sectors == ["Utilities"] and "Gas Utilities" in spec.exclude_industries
    assert apply_filter(_universe(), spec, _mktcap()) == ["0002.HK"]


def test_screen_universe_keyword_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    firm_ids, report = screen_universe("energy, small cap", _universe(), _mktcap())
    assert report["method"] == "keyword"
    assert firm_ids == [] or set(firm_ids) <= {"0003.HK", "0006.HK"}
    # Energy intersect small = nothing; Energy alone:
    firm_ids, report = screen_universe("energy", _universe(), _mktcap())
    assert firm_ids == ["0007.HK"] and report["n_candidates"] == 1


def test_empty_filter_keeps_full_universe():
    firm_ids, _ = screen_universe("I have no particular preference", _universe(), _mktcap())
    assert firm_ids == sorted(_universe()["firm_id"])
