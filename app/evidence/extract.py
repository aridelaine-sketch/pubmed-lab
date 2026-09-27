"""
Evidence extraction.

The core safety property of this module: `select_evidence` on the
decision model returns INDICES ONLY (see decision_model/schemas.py).
This module is the only place that turns an index back into text, and
it always does so by looking the index up in the exact list of
sentences that was sent to the model -- never by trusting text the
model wrote. If the model returns an out-of-range index, we drop it
and log it rather than guessing.
"""

from __future__ import annotations

import logging

from app.decision_model.base import DecisionModel
from app.evidence.provenance import Evidence
from app.pubmed.models import Paper
from app.pubmed.sentence_split import split_sentences

log = logging.getLogger(__name__)


def _numbered_sentences_for_paper(paper: Paper) -> list[tuple[str, str, str]]:
    """Returns (sentence, section, source_type) tuples for every candidate
    sentence in a paper: full text sections if available, else the abstract."""
    out: list[tuple[str, str, str]] = []
    if paper.has_full_text and paper.full_text_sections:
        for section, text in paper.full_text_sections.items():
            for s in split_sentences(text):
                out.append((s, section, "full_text"))
    else:
        for s in split_sentences(paper.abstract):
            out.append((s, "Abstract", "abstract"))
    return out


def extract_evidence(
    model: DecisionModel, claim_or_question: str, paper: Paper
) -> list[Evidence]:
    candidates = _numbered_sentences_for_paper(paper)
    if not candidates:
        return []

    sentences_only = [c[0] for c in candidates]
    batch = model.select_evidence(claim_or_question, sentences_only)

    results: list[Evidence] = []
    for sel in batch.selections:
        if not (0 <= sel.sentence_index < len(candidates)):
            log.warning("Model returned out-of-range sentence_index=%s for pmid=%s; dropped.",
                        sel.sentence_index, paper.pmid)
            continue
        sentence_text, section, source_type = candidates[sel.sentence_index]
        results.append(Evidence(
            sentence=sentence_text,       # <- copied from `candidates`, never from the model's output
            relation=sel.relation,
            confidence=sel.confidence,
            pmid=paper.pmid,
            pmcid=paper.pmcid,
            doi=paper.doi,
            journal=paper.journal,
            year=paper.year,
            first_author_et_al=paper.first_author_et_al,
            section=section,
            source_type=source_type,
            sentence_index=sel.sentence_index,
        ))
    return results
