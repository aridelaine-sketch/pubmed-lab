import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.decision_model.base import DecisionModel
from app.decision_model.schemas import (
    EvidenceSelection, EvidenceSelectionBatch, Relation,
)
from app.evidence.extract import extract_evidence
from app.pubmed.models import Paper


class StubModel(DecisionModel):
    """Returns whatever EvidenceSelectionBatch the test configures."""

    def __init__(self, batch: EvidenceSelectionBatch):
        self._batch = batch

    def select_evidence(self, claim_or_question, numbered_sentences):
        return self._batch

    def classify_intent(self, user_text): raise NotImplementedError
    def generate_search_terms(self, user_text, category): raise NotImplementedError
    def build_learning_structure(self, topic): raise NotImplementedError
    def rank_relevance(self, query, candidate_titles): raise NotImplementedError
    def decide_next_query(self, claim_or_question, evidence_so_far_count, round_number):
        raise NotImplementedError


def make_paper(abstract: str) -> Paper:
    return Paper(pmid="123", title="T", journal="J", year="2020", authors=["Doe J"],
                 doi="10.1/x", abstract=abstract)


def test_extracted_sentence_is_copied_verbatim_from_source():
    paper = make_paper("Statement one is here. Statement two follows after it.")
    batch = EvidenceSelectionBatch(
        selections=[EvidenceSelection(sentence_index=1, relation=Relation.SUPPORT, confidence=0.9)],
        sufficient_evidence=True,
    )
    model = StubModel(batch)
    results = extract_evidence(model, "does X happen?", paper)

    assert len(results) == 1
    assert results[0].sentence == "Statement two follows after it."
    assert results[0].pmid == "123"
    assert results[0].relation == Relation.SUPPORT


def test_out_of_range_index_from_model_is_dropped_not_guessed():
    paper = make_paper("Only one sentence here.")
    batch = EvidenceSelectionBatch(
        selections=[
            EvidenceSelection(sentence_index=0, relation=Relation.SUPPORT, confidence=0.9),
            EvidenceSelection(sentence_index=99, relation=Relation.SUPPORT, confidence=0.9),  # hallucinated index
        ],
        sufficient_evidence=True,
    )
    model = StubModel(batch)
    results = extract_evidence(model, "q", paper)

    assert len(results) == 1  # the bogus index=99 must never produce a result
    assert results[0].sentence == "Only one sentence here."


def test_no_candidate_sentences_returns_empty_list():
    paper = make_paper("")
    model = StubModel(EvidenceSelectionBatch(selections=[], sufficient_evidence=False))
    assert extract_evidence(model, "q", paper) == []


def test_full_text_preferred_over_abstract_when_available():
    paper = Paper(
        pmid="1", title="T", journal="J", year="2020", authors=["A"], doi="",
        abstract="Abstract sentence should not be used.",
        full_text_sections={"Results": "Full text sentence is used instead."},
        has_full_text=True,
    )
    batch = EvidenceSelectionBatch(
        selections=[EvidenceSelection(sentence_index=0, relation=Relation.SUPPORT, confidence=0.8)],
        sufficient_evidence=True,
    )
    model = StubModel(batch)
    results = extract_evidence(model, "q", paper)
    assert results[0].sentence == "Full text sentence is used instead."
    assert results[0].source_type == "full_text"
    assert results[0].section == "Results"
