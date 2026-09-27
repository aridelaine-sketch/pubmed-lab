"""
Typed decision schemas.

The core rule of this whole application: the local model NEVER returns
free-form scientific prose. It only ever returns one of the structures
below. Every field here is either an enum, a number, or an index into
data the caller already owns (sentence numbers, paper ids). The model
cannot invent a PMID, cannot invent a sentence, and cannot write a
citation — it can only *point at* things that already exist in the
PubMed/PMC response.

This is the same idea behind "typed decision" models (Jev/Kev-style
System-One models): state in, typed choice out. We implement the
pattern ourselves with JSON-schema-constrained decoding on a small
open-weight model, so the app never depends on a single vendor.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    LEARN = "learn"
    QUESTION = "question"
    CLAIM = "claim"


class Relation(str, Enum):
    SUPPORT = "support"
    CONTRADICT = "contradict"
    QUALIFY = "qualify"
    IRRELEVANT = "irrelevant"


class IntentDecision(BaseModel):
    intent: Intent
    category: str = Field(..., description="Short clinical/scientific category, e.g. 'pulmonary vascular disease'")
    confidence: float = Field(..., ge=0.0, le=1.0)


class SearchTermSet(BaseModel):
    """PubMed-syntax search strings the model proposes. Nothing else."""
    terms: list[str] = Field(..., min_length=1, max_length=5)


class LearningSection(BaseModel):
    title: str
    rationale: str = Field(..., description="One short phrase: why this section belongs here")


class LearningStructure(BaseModel):
    topic: str
    sections: list[LearningSection] = Field(..., min_length=3, max_length=12)


class RelevanceDecision(BaseModel):
    """Ranks candidate PMIDs the caller supplied. Index-based, not text."""
    ranked_indices: list[int]
    keep_top_n: int


class EvidenceSelection(BaseModel):
    """
    The single most important schema in the app.

    `sentence_index` values must correspond exactly to the numbered
    sentence list the caller sent in the prompt. The model never writes
    sentence text itself — the caller looks the index up in the
    original source string. This is what makes fabricated quotes
    structurally impossible rather than merely discouraged.
    """
    sentence_index: int
    relation: Relation
    confidence: float = Field(..., ge=0.0, le=1.0)


class EvidenceSelectionBatch(BaseModel):
    selections: list[EvidenceSelection]
    sufficient_evidence: bool = Field(
        ..., description="False if the model thinks another search round is needed"
    )


class NextQuery(BaseModel):
    should_search_again: bool
    reason: str
    new_terms: Optional[list[str]] = None
