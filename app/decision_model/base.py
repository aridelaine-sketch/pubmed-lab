"""
DecisionModel: the abstraction that lets the local model be swapped
without touching the PubMed engine, the evidence layer, or the UI.

Every backend (Ollama, llama.cpp, a fake offline backend for tests,
or an API model) implements this same interface. The orchestrator
only ever talks to this class, never to a specific runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.decision_model.schemas import (
    EvidenceSelectionBatch,
    IntentDecision,
    LearningStructure,
    NextQuery,
    RelevanceDecision,
    SearchTermSet,
)


class DecisionModel(ABC):
    """All methods return typed pydantic objects, never raw strings."""

    @abstractmethod
    def classify_intent(self, user_text: str) -> IntentDecision:
        ...

    @abstractmethod
    def generate_search_terms(self, user_text: str, category: str) -> SearchTermSet:
        ...

    @abstractmethod
    def build_learning_structure(self, topic: str) -> LearningStructure:
        ...

    @abstractmethod
    def rank_relevance(self, query: str, candidate_titles: list[str]) -> RelevanceDecision:
        ...

    @abstractmethod
    def select_evidence(
        self, claim_or_question: str, numbered_sentences: list[str]
    ) -> EvidenceSelectionBatch:
        ...

    @abstractmethod
    def decide_next_query(
        self, claim_or_question: str, evidence_so_far_count: int, round_number: int
    ) -> NextQuery:
        ...
