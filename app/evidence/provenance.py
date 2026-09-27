from __future__ import annotations

from dataclasses import dataclass

from app.decision_model.schemas import Relation


@dataclass
class Evidence:
    sentence: str          # copied verbatim from the source text by CODE, never written by the model
    relation: Relation
    confidence: float
    pmid: str
    pmcid: str | None
    doi: str
    journal: str
    year: str
    first_author_et_al: str
    section: str            # "Abstract" or a full-text section name
    source_type: str        # "full_text" | "abstract"
    sentence_index: int
