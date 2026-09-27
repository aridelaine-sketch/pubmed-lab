"""
The orchestrator is intentionally thin: it makes no scientific
judgment itself. Every branch point (what to search, whether a
sentence supports/contradicts, whether to search again) is delegated
to the DecisionModel. This module's only job is sequencing:

    decide -> search PubMed -> extract evidence -> decide again -> render
"""

from __future__ import annotations

from dataclasses import dataclass

from app.decision_model.base import DecisionModel
from app.decision_model.schemas import Intent
from app.evidence.extract import extract_evidence
from app.evidence.provenance import Evidence
from app.export import markdown as md
from app.pubmed.engine import PubMedEngine
from app.storage.db import Store

MAX_SEARCH_ROUNDS = 3
PAPERS_PER_SEARCH = 6


@dataclass
class RunResult:
    markdown: str
    note_type: str
    topic: str
    saved_path: str | None = None


def _gather_evidence(
    model: DecisionModel, engine: PubMedEngine, claim_or_question: str, terms: list[str], store: Store
) -> list[Evidence]:
    all_evidence: list[Evidence] = []
    round_number = 1
    tried_terms = set()
    seen_pmids = set()  # the same paper often surfaces under several related search terms;
    # extract it once, not once per term, or evidence gets duplicated in the note.
    while round_number <= MAX_SEARCH_ROUNDS:
        for term in terms:
            if term in tried_terms:
                continue
            tried_terms.add(term)
            papers = engine.search(term, retmax=PAPERS_PER_SEARCH)
            for paper in papers:
                if paper.pmid in seen_pmids:
                    continue
                seen_pmids.add(paper.pmid)
                store.upsert_paper(paper)  # cache metadata locally regardless of relevance
                all_evidence.extend(extract_evidence(model, claim_or_question, paper))

        decision = model.decide_next_query(claim_or_question, len(all_evidence), round_number)
        if not decision.should_search_again or not decision.new_terms:
            break
        terms = decision.new_terms
        round_number += 1
    return all_evidence


def run_question(model: DecisionModel, engine: PubMedEngine, store: Store, question: str) -> RunResult:
    intent_decision = model.classify_intent(question)
    query_id = store.insert_query(question, Intent.QUESTION.value, intent_decision.category)

    terms = model.generate_search_terms(question, intent_decision.category).terms
    evidence = _gather_evidence(model, engine, question, terms, store)

    for e in evidence:
        store.insert_evidence(query_id, e)

    text = md.render_question(question, intent_decision.category, evidence)
    return RunResult(markdown=text, note_type="question", topic=question)


def run_claim(model: DecisionModel, engine: PubMedEngine, store: Store, claim: str) -> RunResult:
    intent_decision = model.classify_intent(claim)
    query_id = store.insert_query(claim, Intent.CLAIM.value, intent_decision.category)

    terms = model.generate_search_terms(claim, intent_decision.category).terms
    evidence = _gather_evidence(model, engine, claim, terms, store)

    for e in evidence:
        store.insert_evidence(query_id, e)

    text = md.render_claim(claim, intent_decision.category, evidence)
    return RunResult(markdown=text, note_type="claim", topic=claim)


def run_learn(model: DecisionModel, engine: PubMedEngine, store: Store, topic: str) -> RunResult:
    intent_decision = model.classify_intent(f"I want to learn {topic}")
    query_id = store.insert_query(topic, Intent.LEARN.value, intent_decision.category)

    structure = model.build_learning_structure(topic)
    section_evidence: dict[str, list[Evidence]] = {}

    for section in structure.sections:
        section_query = f"{topic} {section.title}"
        terms = model.generate_search_terms(section_query, intent_decision.category).terms
        evidence = _gather_evidence(model, engine, section_query, terms, store)
        section_evidence[section.title] = evidence
        for e in evidence:
            store.insert_evidence(query_id, e, note_section=section.title)

    text = md.render_learn(topic, section_evidence, intent_decision.category)
    return RunResult(markdown=text, note_type="learn", topic=topic)


def dispatch(model: DecisionModel, engine: PubMedEngine, store: Store, user_text: str) -> RunResult:
    """Entry point the UI calls: classify first, then route."""
    intent_decision = model.classify_intent(user_text)
    if intent_decision.intent == Intent.LEARN:
        topic = user_text.lower().split("learn", 1)[-1].strip(" .?!") or user_text
        return run_learn(model, engine, store, topic)
    if intent_decision.intent == Intent.CLAIM:
        return run_claim(model, engine, store, user_text)
    return run_question(model, engine, store, user_text)
