"""Structured-output schema for the talk/walk rubric (pydantic). Field descriptions are part of the prompt."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Commitment(BaseModel):
    text: str = Field(description="Verbatim or near-verbatim quote of the commitment/claim")
    kind: str = Field(description="'target' (future), 'achievement' (realised), 'investment', 'policy', 'other'")
    quantified: bool = Field(description="Has a number, baseline and/or date")
    horizon_year: int | None = Field(description="Year the target refers to, if any")


class TalkScores(BaseModel):
    ambition: float = Field(ge=0, le=10, description="How ambitious the climate/ESG language is (net zero, leadership claims)")
    specificity: float = Field(ge=0, le=10, description="Targets with numbers, baselines, scopes and dates vs vague aspirations")
    forward_looking_share: float = Field(ge=0, le=10, description="10 = almost all climate statements are about the future, 0 = mostly realised past actions")
    hedging: float = Field(ge=0, le=10, description="Use of 'aim', 'aspire', 'may', 'subject to' around climate claims; 10 = heavily hedged")
    promotional_tone: float = Field(ge=0, le=10, description="Marketing/self-congratulatory framing of environmental performance")


class WalkScores(BaseModel):
    realised_reductions: float = Field(ge=0, le=10, description="Documented, quantified past emission/intensity reductions")
    capital_deployed: float = Field(ge=0, le=10, description="Concrete capex/opex in low-carbon assets, with amounts")
    verification: float = Field(ge=0, le=10, description="Third-party assurance, SBTi validation, audited metrics, regulatory filings")
    governance: float = Field(ge=0, le=10, description="Board oversight, executive pay linked to climate metrics, named accountable roles")
    hard_data_consistency: float = Field(ge=0, le=10, description="Do the claims agree with the HARD DATA block supplied? 10 = fully consistent, 0 = contradicted")
    implementation_share: float = Field(ge=0, le=10, description="Of all environment-related content, the share about implementation/operations/technology/capex (walk) versus metrics preparation, reporting, marketing, advocacy, PR (talk). 10 = almost all implementation (Chen 2025 task rule)")


class TalkWalkScore(BaseModel):
    climate_relevance: float = Field(ge=0, le=10, description="How much of the text is actually about climate/environment")
    talk: TalkScores
    walk: WalkScores
    commitments: list[Commitment] = Field(description="Up to 10 most important commitments or claims")
    evidence_talk: list[str] = Field(description="2-4 short quotes that drove the talk scores")
    evidence_walk: list[str] = Field(description="2-4 short quotes that drove the walk scores")
    summary: str = Field(description="Two sentences: what the firm says vs what it demonstrably does")


