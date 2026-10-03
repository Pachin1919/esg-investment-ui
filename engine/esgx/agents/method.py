"""Snapshot of the parameters the measurement layer actually runs with (for the How-it-works page)."""

from __future__ import annotations

from typing import Any

from esgx.agents.pipeline import USD_PER_REVIEW, USD_PER_SECTION
from esgx.config import EMISSIONS_PUBLICATION_LAG_MONTHS, END_YEAR, START_YEAR
from esgx.ingest.edgar_text import CLIMATE_TERMS, MIN_SECTION_CHARS, SECTIONS_10K
from esgx.measures import custom_score
from esgx.measures import talkwalk as tw
from esgx.measures import text_measures as tm


def method_snapshot() -> dict[str, Any]:
    return {
        "rubric_version": tw.RUBRIC_VERSION,
        "model": tw.DEFAULT_MODEL,
        "system_prompt": tw.SYSTEM_PROMPT,
        "talk_fields": tw.TALK_FIELDS,
        "walk_fields": tw.WALK_FIELDS,
        "talk_weights": tw.TALK_WEIGHTS,
        "walk_weights": tw.WALK_WEIGHTS,
        "form_weights": tw.FORM_WEIGHTS,
        "sections_10k": SECTIONS_10K,
        "min_section_chars": MIN_SECTION_CHARS,
        "climate_terms": CLIMATE_TERMS,
        "env_terms": tm.ENV_TERMS,
        "forward_terms": tm.FORWARD_TERMS,
        "realised_terms": tm.REALISED_TERMS,
        "custom_score_weights": custom_score.DEFAULT_WEIGHTS,
        "sample": {"start_year": START_YEAR, "end_year": END_YEAR, "emissions_lag_months": EMISSIONS_PUBLICATION_LAG_MONTHS},
        "greenness": {"formula": "g = -(10 - e_score) * e_weight / 100", "e_weight_range": [5, 50],
                      "e_score": "within-industry percentile rank of scope-1 intensity, method=min (ties at zero are cleanest)",
                      "e_weight": "industry percentile rank of aggregate intensity, mapped to 5..50"},
        "gmb": {"sorted": "value-weighted top-tercile g minus bottom-tercile g, monthly rebalance",
                "regression": "cross-sectional regression of market-adjusted excess returns on g, no intercept, 60-month betas"},
        "cost": {"usd_per_section": USD_PER_SECTION, "usd_per_review": USD_PER_REVIEW, "basis": "XOM pilot, 12 sections, 0.95 USD"},
    }
