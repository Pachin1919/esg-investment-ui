"""LLM-scored "talk" vs "walk" on firm documents (Lecture 11: greenwashing = words > actions).

Design
------
* Input: one document section (10-K item, 10-Q MD&A, 8-K press release), pre-filtered to
  climate-relevant passages, plus HARD DATA we already hold for the firm-year (scope-1 trend
  and intensity from GHGRP, revenue) so the model can check claims against facts.
* Output: a fixed rubric (pydantic `TalkWalkScore`) with 0-10 sub-scores, a short list of
  extracted quantitative commitments, and quoted evidence. Rubric dimensions follow the
  literature (Chen 2022 talk/walk, Giannetti et al. 2023 disclosure vs lending, Liang et al.
  2022 signatory vs holdings, Gourier-Mathurin 2025 salience):
    talk : ambition, specificity, forward-looking share, hedging, promotional tone
    walk : realised reductions, capital deployed, verification, governance, hard-data consistency
* Aggregation: firm-year TALK and WALK pillars in [0, 10], GAP = TALK - WALK (+ = greenwashing risk).
* Every call is cached on (accession, section, rubric_version, model) so re-runs are free.

Model: claude-opus-5 by default (thinking is on by default; effort configurable).
Requires ANTHROPIC_API_KEY (or an `ant auth login` profile). Use `DryRunClient` in tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from esgx.config import RAW_DIR
from esgx.ingest.edgar_text import climate_passages
from esgx.measures.hard_data import hard_data_for
from esgx.measures.talkwalk_clients import CacheOnlyClient, ClaudeClient, DryRunClient, ScoreClient
from esgx.measures.talkwalk_schema import Commitment, TalkScores, TalkWalkScore, WalkScores

RUBRIC_VERSION = "v2"
DEFAULT_MODEL = "claude-opus-5"

__all__ = ["CacheOnlyClient", "ClaudeClient", "Commitment", "DryRunClient", "ScoreClient", "TalkScores", "TalkWalkScore", "WalkScores", "hard_data_for"]


TALK_FIELDS = ["ambition", "specificity", "forward_looking_share", "hedging", "promotional_tone"]
WALK_FIELDS = ["realised_reductions", "capital_deployed", "verification", "governance", "hard_data_consistency", "implementation_share"]

# how sub-scores roll up: talk = ambition + specificity-adjusted claims; hedging lowers credibility, not talk
TALK_WEIGHTS = {"ambition": 0.4, "forward_looking_share": 0.3, "promotional_tone": 0.3}
WALK_WEIGHTS = {"realised_reductions": 0.25, "capital_deployed": 0.2, "verification": 0.15, "governance": 0.1, "hard_data_consistency": 0.15, "implementation_share": 0.15}

SYSTEM_PROMPT = """You are a sustainable-finance analyst scoring corporate disclosures for a research project on greenwashing.
You separate what a company SAYS (talk) from what it demonstrably DOES (walk), following the academic literature
(Chen 2022 "talk the talk or walk the walk"; Giannetti et al. 2023 "Glossy green banks"; Liang, Sun & Teo 2022).

Rules
- Score only from the supplied text and the HARD DATA block. Do not use outside knowledge about the company.
- 'Walk' needs numbers, dates, realised outcomes, money spent, or third-party verification. Aspirations, pledges,
  memberships and 'we are committed to' language are TALK, not walk.
- If the text barely discusses climate/environment, give low climate_relevance and keep all sub-scores near the
  neutral middle (5) rather than guessing.
- Quote evidence verbatim and briefly. Extract up to 10 commitments. Do not infer, invent or speculate beyond the text.
- Exclusions: discussion of climate RISKS to the business, lobbying/political positions, and unintended drawbacks of
  green products are neither talk nor walk; do not let them raise or lower the scores.
- Implementation test (Chen 2025): content counts as WALK only if it directly changes environmental outcomes
  (operations, technology, capex, procurement). Metrics preparation, reporting, marketing, memberships and PR are TALK.
- Be strict and consistent: a 10 is exceptional, a 0 is absent."""


def _user_prompt(firm_name: str, form: str, section: str, period: str, hard_data: dict, text: str) -> str:
    hd = json.dumps(hard_data, indent=1, default=str) if hard_data else "none available"
    return f"""COMPANY: {firm_name}
DOCUMENT: {form}, section '{section}', period ending {period}

HARD DATA (from EPA GHGRP facility reports and SEC financials; tCO2e, USD millions):
{hd}

TEXT (climate-relevant passages only):
<document>
{text}
</document>

Score the document on the rubric."""


# ---------------------------------------------------------------- scoring with cache
CACHE_DIR = RAW_DIR / "llm_cache"


def _cache_key(accession: str, section: str, model: str, text: str, system: str = SYSTEM_PROMPT) -> Path:
    variant = "" if system == SYSTEM_PROMPT else "|" + hashlib.sha1(system.encode()).hexdigest()[:8]
    h = hashlib.sha1(f"{RUBRIC_VERSION}{variant}|{model}|{accession}|{section}|{text[:2000]}".encode()).hexdigest()[:20]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{h}.json"


def score_document(
    client: ScoreClient,
    firm_name: str,
    row: pd.Series,
    hard_data: dict | None,
    max_chars: int = 60_000,
    system: str = SYSTEM_PROMPT,
    talk_weights: dict[str, float] | None = None,
    walk_weights: dict[str, float] | None = None,
) -> dict:
    """Score one `documents` row. Returns flat dict with sub-scores, aggregates and usage.
    `system` lets an agent run a rubric variant (extra instructions); variants get their own cache key."""
    talk_weights = talk_weights or TALK_WEIGHTS
    walk_weights = walk_weights or WALK_WEIGHTS
    text = row["text"]
    if row["section"] != "full_climate":
        text, share = climate_passages(text, max_chars=max_chars)
    else:
        share = float("nan")
        text = text[:max_chars]
    model = getattr(client, "model", "dry-run")
    path = _cache_key(row["accession"], row["section"], model, text, system)
    if path.exists():
        cached = json.loads(path.read_text())
        parsed, usage = TalkWalkScore.model_validate(cached["score"]), cached["usage"]
    else:
        if len(text) < 300:
            return {**_meta(row), "climate_share": share, "skipped": True, "skip_reason": "too_short"}
        if getattr(client, "cache_only", False):
            return {**_meta(row), "climate_share": share, "skipped": True, "skip_reason": "cache_miss"}
        parsed, usage = client.score(system, _user_prompt(firm_name, row["form"], row["section"], row["period"], hard_data or {}, text))
        path.write_text(json.dumps({"score": parsed.model_dump(), "usage": usage}))
    d = {**_meta(row), "climate_share": share, "skipped": False, "climate_relevance": parsed.climate_relevance}
    for f in TALK_FIELDS:
        d[f"talk_{f}"] = getattr(parsed.talk, f)
    for f in WALK_FIELDS:
        d[f"walk_{f}"] = getattr(parsed.walk, f)
    d["talk"] = sum(w * getattr(parsed.talk, k) for k, w in talk_weights.items())
    d["walk"] = sum(w * getattr(parsed.walk, k) for k, w in walk_weights.items())
    d["gap"] = d["talk"] - d["walk"]
    d["n_commitments"] = len(parsed.commitments)
    d["n_quantified"] = sum(c.quantified for c in parsed.commitments)
    d["summary"] = parsed.summary
    d["evidence_talk"] = json.dumps(parsed.evidence_talk)
    d["evidence_walk"] = json.dumps(parsed.evidence_walk)
    d["commitments"] = json.dumps([c.model_dump() for c in parsed.commitments])
    d.update({f"usage_{k}": v for k, v in usage.items()})
    return d


def _meta(row: pd.Series) -> dict:
    return {k: row[k] for k in ["firm_id", "form", "filing_date", "period", "accession", "section"]}


FORM_WEIGHTS = {"10-K": 2.0}


def aggregate_firm_year(scores: pd.DataFrame, form_weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Document scores -> firm × year pillars (0-10) weighted by climate relevance.
    Year = fiscal year of the period end. 10-K weight 2, others 1 (`form_weights`)."""
    form_weights = form_weights or FORM_WEIGHTS
    df = scores[~scores["skipped"]].copy()
    if df.empty:
        return pd.DataFrame(columns=["firm_id", "year", "talk", "walk", "gap", "n_docs"])
    df["year"] = pd.to_datetime(df["period"]).dt.year
    df["w"] = (df["climate_relevance"].clip(lower=0.5)) * df["form"].map(form_weights).fillna(1.0)
    cols = ["talk", "walk", "gap"] + [f"talk_{f}" for f in TALK_FIELDS] + [f"walk_{f}" for f in WALK_FIELDS]

    def _wavg(g: pd.DataFrame) -> pd.Series:
        out = {c: (g[c] * g["w"]).sum() / g["w"].sum() for c in cols}
        out["n_docs"] = len(g)
        return pd.Series(out)

    return df.groupby(["firm_id", "year"]).apply(_wavg, include_groups=False).reset_index()
