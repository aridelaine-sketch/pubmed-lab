"""
FakeBackend: a deterministic, offline stand-in for a real local model.

This is NOT a shortcut around the architecture — it implements the exact
same DecisionModel interface as OllamaBackend using simple heuristics
instead of an LLM call. It exists for two reasons:

1. Unit tests should not depend on a running Ollama process or GPU.
2. It lets us prove, inside a network-sandboxed environment, that the
   orchestrator + PubMed engine + evidence layer + markdown export all
   work correctly end to end — with the ONLY thing swapped out being
   this one file. That swap is the entire point of the abstraction.

Replace `FakeBackend()` with `OllamaBackend()` anywhere it's constructed
and nothing else in the app needs to change.
"""

from __future__ import annotations

import re

from app.decision_model.base import DecisionModel
from app.decision_model.schemas import (
    EvidenceSelection,
    EvidenceSelectionBatch,
    Intent,
    IntentDecision,
    LearningSection,
    LearningStructure,
    NextQuery,
    Relation,
    RelevanceDecision,
    SearchTermSet,
)

_NEGATION_MARKERS = ("no association", "not associated", "did not", "no significant",
                     "failed to", "no evidence", "unrelated", "however", "in contrast")
_QUALIFIER_MARKERS = ("in patients with", "only when", "except", "limited to",
                       "in a subset", "depending on", "among patients")
_CLAIM_MARKERS = (" is associated", " causes", " leads to", " increases", " decreases",
                   " is a risk factor", " is caused by")


class FakeBackend(DecisionModel):
    """Keyword/heuristic implementation — see module docstring."""

    def classify_intent(self, user_text: str) -> IntentDecision:
        t = user_text.strip().lower()
        if t.startswith(("i want to learn", "learn ", "teach me", "explain")):
            intent, cat = Intent.LEARN, self._guess_category(t)
        elif "?" in user_text or t.startswith(("why", "how", "what", "when", "does")):
            intent, cat = Intent.QUESTION, self._guess_category(t)
        elif any(m in t for m in _CLAIM_MARKERS):
            intent, cat = Intent.CLAIM, self._guess_category(t)
        else:
            intent, cat = Intent.QUESTION, self._guess_category(t)
        return IntentDecision(intent=intent, category=cat, confidence=0.7)

    def _guess_category(self, t: str) -> str:
        if "pulmonary" in t or "lung" in t or "hemoptysis" in t or "eisenmenger" in t:
            return "pulmonary vascular disease"
        if "copd" in t:
            return "obstructive lung disease"
        return "general medicine"

    def generate_search_terms(self, user_text: str, category: str) -> SearchTermSet:
        words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", user_text)
        stop = {"what", "does", "cause", "causes", "does", "learn", "want", "about", "explain"}
        keywords = [w for w in words if w.lower() not in stop][:4]
        base = " AND ".join(keywords) if keywords else category
        return SearchTermSet(terms=[base, f"{base} AND review[pt]"])

    def build_learning_structure(self, topic: str) -> LearningStructure:
        sections = [
            LearningSection(title="Definition", rationale="ground the term before anything else"),
            LearningSection(title="Classification", rationale="most clinical topics split into subtypes"),
            LearningSection(title="Epidemiology", rationale="who is affected, how often"),
            LearningSection(title="Pathophysiology", rationale="mechanism drives everything downstream"),
            LearningSection(title="Clinical manifestations", rationale="how it presents"),
            LearningSection(title="Diagnosis", rationale="how it's confirmed"),
            LearningSection(title="Treatment", rationale="management options"),
            LearningSection(title="Prognosis", rationale="expected course"),
        ]
        return LearningStructure(topic=topic, sections=sections)

    def rank_relevance(self, query: str, candidate_titles: list[str]) -> RelevanceDecision:
        q_words = set(re.findall(r"[a-z]+", query.lower()))
        scored = []
        for i, title in enumerate(candidate_titles):
            t_words = set(re.findall(r"[a-z]+", title.lower()))
            scored.append((i, len(q_words & t_words)))
        scored.sort(key=lambda x: -x[1])
        return RelevanceDecision(ranked_indices=[i for i, _ in scored], keep_top_n=min(5, len(scored)))

    def select_evidence(self, claim_or_question: str, numbered_sentences: list[str]) -> EvidenceSelectionBatch:
        selections = []
        q_words = set(re.findall(r"[a-z]{4,}", claim_or_question.lower()))
        for i, sentence in enumerate(numbered_sentences):
            s_lower = sentence.lower()
            s_words = set(re.findall(r"[a-z]{4,}", s_lower))
            overlap = len(q_words & s_words)
            if overlap == 0:
                continue
            if any(m in s_lower for m in _NEGATION_MARKERS):
                relation = Relation.CONTRADICT
            elif any(m in s_lower for m in _QUALIFIER_MARKERS):
                relation = Relation.QUALIFY
            else:
                relation = Relation.SUPPORT
            confidence = min(0.95, 0.4 + 0.15 * overlap)
            selections.append(EvidenceSelection(sentence_index=i, relation=relation, confidence=confidence))
        return EvidenceSelectionBatch(selections=selections, sufficient_evidence=len(selections) > 0)

    def decide_next_query(self, claim_or_question: str, evidence_so_far_count: int, round_number: int) -> NextQuery:
        if evidence_so_far_count >= 2 or round_number >= 2:
            return NextQuery(should_search_again=False, reason="enough evidence gathered")
        return NextQuery(
            should_search_again=True,
            reason="too little evidence in round 1",
            new_terms=[claim_or_question.split(" is ")[0].strip() or claim_or_question],
        )
