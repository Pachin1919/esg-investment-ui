"""Preference screening: an investor's free-text stock preferences -> the candidate subset
that `portfolio.recommend` is allowed to consider.

Two screeners, same output schema:

* `screen_llm` — the AI agent. Kimi K3 (or any configured model) translates the free text
  into a `PreferenceFilter`, choosing only from the actual sector/industry/country values
  of the universe (same prompt discipline as the source finders: never invent values).
* `screen_keywords` — deterministic fallback when no API key is configured: size words
  ("large cap") and exact value matches. Heuristic output is a convenience, never a result.

`apply_filter` is always deterministic: the model proposes, the code disposes. The screen
block in the API response shows the interpretation so the user can correct it.
"""

from __future__ import annotations

import os
import re

import pandas as pd
from pydantic import BaseModel, Field

from esgx import llm

SCREEN_PROMPT = """You are given an investor's free-text stock preferences and the available filter
values of the investable universe (sectors, industries, countries). Translate the preferences into
a filter. Rules:
- Use only values from the supplied lists, with exact spelling. Do not invent or generalize values.
- include_*: the user expresses interest (e.g. "I like banks and tech"). Include restricts the universe.
- exclude_*: the user rejects (e.g. "avoid energy", "no casinos"). Exclusion wins over inclusion.
- countries: restrict to these markets only if the user names a geography.
- size: one or more of large / mid / small, only if the user mentions market cap size.
- keywords: business themes the lists cannot express (e.g. "AI", "dividend", "gaming"); matched
  against company names. Leave empty when sector/industry values cover the request.
- If the text contains no filterable preference, return empty lists.
- rationale: one short sentence describing the interpretation."""

_SIZE = ("large", "mid", "small")


class PreferenceFilter(BaseModel):
    include_sectors: list[str] = Field(default_factory=list)
    include_industries: list[str] = Field(default_factory=list)
    exclude_sectors: list[str] = Field(default_factory=list)
    exclude_industries: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    size: list[str] = Field(default_factory=list, description="subset of large, mid, small")
    keywords: list[str] = Field(default_factory=list)
    rationale: str = ""


def _values(universe: pd.DataFrame) -> dict[str, list[str]]:
    return {c: sorted(universe[c].dropna().unique()) for c in ("sector", "industry", "country")}


def _sanitize(spec: PreferenceFilter, values: dict[str, list[str]]) -> PreferenceFilter:
    """Keep only filter values that exist in the universe; the model may still paraphrase."""
    spec.include_sectors = [v for v in spec.include_sectors if v in values["sector"]]
    spec.include_industries = [v for v in spec.include_industries if v in values["industry"]]
    spec.exclude_sectors = [v for v in spec.exclude_sectors if v in values["sector"]]
    spec.exclude_industries = [v for v in spec.exclude_industries if v in values["industry"]]
    spec.countries = [v for v in spec.countries if v in values["country"]]
    spec.size = [s for s in spec.size if s in _SIZE]
    return spec


def screen_llm(text: str, universe: pd.DataFrame, model: str | None = None,
               effort: str = "low") -> PreferenceFilter:
    values = _values(universe)
    catalog = (f"SECTORS: {values['sector']}\nINDUSTRIES: {values['industry']}\n"
               f"COUNTRIES: {values['country']}")
    spec, _ = llm.parse(model or llm.PRIMARY_MODEL, SCREEN_PROMPT,
                        f"PREFERENCES: {text}\n\n{catalog}", PreferenceFilter, effort=effort)
    return _sanitize(spec, values)


def screen_keywords(text: str, universe: pd.DataFrame) -> PreferenceFilter:
    """Keyword heuristic: size words and exact matches of universe values (whole-word, case-insensitive).
    'avoid/no/without/exclude X' turns the matched value into an exclusion, matched on any
    significant word of the value ("no gas" excludes both "Gas Utilities" and "Oil & Gas")."""
    t = text.lower()
    size = [s for s in _SIZE if re.search(rf"\b{s}[\s-]?cap\b", t)]
    neg = re.findall(r"(?:avoid|without|no|exclude|except|not)\s+([a-z][a-z &/-]{1,30})", t)
    values = _values(universe)

    def hits(vals: list[str]) -> list[str]:
        return [v for v in vals if re.search(rf"\b{re.escape(v.lower())}\b", t)]

    def neg_hits(vals: list[str]) -> list[str]:
        generic = {"utilities", "the", "and", "group", "holdings", "services", "industries", "products"}
        out = []
        for phrase in neg:
            for v in vals:
                words = {w for w in re.split(r"[ &/-]+", v.lower()) if len(w) >= 3} - generic
                if words & set(phrase.split()):
                    out.append(v)
        return out

    exc_s, exc_i = neg_hits(values["sector"]), neg_hits(values["industry"])
    return PreferenceFilter(
        include_sectors=[v for v in hits(values["sector"]) if v not in exc_s],
        include_industries=[v for v in hits(values["industry"]) if v not in exc_i],
        exclude_sectors=exc_s,
        exclude_industries=exc_i,
        countries=hits(values["country"]),
        size=size,
        rationale="keyword match (no LLM configured)",
    )


def apply_filter(universe: pd.DataFrame, spec: PreferenceFilter, mktcap: pd.Series) -> list[str]:
    """Deterministic filter. Includes are OR within a dimension and AND across dimensions;
    exclusions always win; size is a tercile of latest market cap within the universe."""
    df = universe.drop_duplicates("firm_id").set_index("firm_id")
    mask = pd.Series(True, index=df.index)
    if spec.include_sectors:
        mask &= df["sector"].isin(spec.include_sectors)
    if spec.include_industries:
        mask &= df["industry"].isin(spec.include_industries)
    if spec.countries:
        mask &= df["country"].isin(spec.countries)
    if spec.keywords:
        pat = "|".join(re.escape(k.lower()) for k in spec.keywords)
        mask &= df["name"].str.lower().str.contains(pat, regex=True)
    if spec.size:
        pct = mktcap.reindex(df.index).rank(pct=True)
        size_mask = pd.Series(False, index=df.index)
        for s in spec.size:
            lo, hi = {"small": (0.0, 1 / 3), "mid": (1 / 3, 2 / 3), "large": (2 / 3, 1.0)}[s]
            size_mask |= (pct > lo) & (pct <= hi)
        mask &= size_mask
    if spec.exclude_sectors:
        mask &= ~df["sector"].isin(spec.exclude_sectors)
    if spec.exclude_industries:
        mask &= ~df["industry"].isin(spec.exclude_industries)
    return sorted(df.index[mask])


def llm_available() -> bool:
    return bool(os.environ.get("MOONSHOT_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def screen_universe(text: str, universe: pd.DataFrame, mktcap: pd.Series,
                    model: str | None = None) -> tuple[list[str], dict]:
    """Free text -> (candidate firm_ids, screen report). LLM when configured, keywords otherwise;
    an LLM failure falls back to keywords and says so in the report."""
    method = model or llm.PRIMARY_MODEL
    if llm_available():
        try:
            spec = screen_llm(text, universe, model=model)
        except Exception:  # noqa: BLE001 - a screening failure must not kill the recommendation
            spec, method = screen_keywords(text, universe), "keyword (llm failed)"
    else:
        spec, method = screen_keywords(text, universe), "keyword"
    firm_ids = apply_filter(universe, spec, mktcap)
    report = {"method": method, "spec": spec.model_dump(), "n_candidates": len(firm_ids),
              "rationale": spec.rationale}
    return firm_ids, report
