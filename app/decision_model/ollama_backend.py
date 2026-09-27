"""
Ollama-backed DecisionModel.

Uses Ollama's /api/chat endpoint with `format=<json schema>`, which
constrains decoding at the token level: the model literally cannot
emit a token that would break the schema. This is what turns a
general-purpose chat model into a "typed decision" engine without
depending on any single vendor's proprietary decision model.

Swap to llama.cpp instead: implement LlamaCppBackend with the same
interface, pointed at llama-server's /v1/chat/completions with
response_format={"type": "json_schema", ...}. The orchestrator would
not change a single line.
"""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from app.decision_model.base import DecisionModel
from app.decision_model.schemas import (
    EvidenceSelectionBatch,
    IntentDecision,
    LearningStructure,
    NextQuery,
    RelevanceDecision,
    SearchTermSet,
)

SYSTEM_PROMPT = """You are a routing and decision layer for a medical evidence tool.
You NEVER state medical facts from memory. You only classify, rank, choose,
and select indices from data the user provides. If asked to select evidence,
you may only return sentence_index values that were present in the numbered
list you were given. Never invent an index."""


class OllamaBackend(DecisionModel):
    def __init__(self, model: str = "qwen3:8b", host: str = "http://localhost:11434", timeout: float = 60.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _call(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": schema.model_json_schema(),
            "stream": False,
            "options": {"temperature": 0.1},
        }
        resp = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return schema.model_validate(json.loads(content))

    def classify_intent(self, user_text: str) -> IntentDecision:
        prompt = f"Classify this user input.\n\nInput: {user_text!r}\n\n" \
                 f"intent must be one of: learn, question, claim."
        return self._call(prompt, IntentDecision)  # type: ignore[return-value]

    def generate_search_terms(self, user_text: str, category: str) -> SearchTermSet:
        prompt = (
            f"Category: {category}\nUser input: {user_text!r}\n\n"
            "Propose 1-5 PubMed-syntax search strings (use AND/OR, [MeSH Terms], "
            "[Title/Abstract] as needed) that would retrieve relevant literature."
        )
        return self._call(prompt, SearchTermSet)  # type: ignore[return-value]

    def build_learning_structure(self, topic: str) -> LearningStructure:
        prompt = (
            f"Topic: {topic!r}\n\n"
            "Propose an evidence-based learning structure (3-12 sections) appropriate "
            "SPECIFICALLY for this topic. Do not reuse a generic disease template unless "
            "it genuinely fits — a physiology topic, a procedure, and a drug class each "
            "need a different structure."
        )
        return self._call(prompt, LearningStructure)  # type: ignore[return-value]

    def rank_relevance(self, query: str, candidate_titles: list[str]) -> RelevanceDecision:
        numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(candidate_titles))
        prompt = (
            f"Query: {query!r}\n\nCandidate paper titles:\n{numbered}\n\n"
            "Return ranked_indices (best first, using ONLY the [i] indices above) "
            "and keep_top_n."
        )
        return self._call(prompt, RelevanceDecision)  # type: ignore[return-value]

    def select_evidence(self, claim_or_question: str, numbered_sentences: list[str]) -> EvidenceSelectionBatch:
        numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(numbered_sentences))
        prompt = (
            f"Claim or question: {claim_or_question!r}\n\n"
            f"Numbered sentences from a real PubMed/PMC source:\n{numbered}\n\n"
            "For each sentence that is relevant, return its index EXACTLY as shown "
            "in brackets, and classify its relation to the claim/question as "
            "support, contradict, qualify, or irrelevant. Only include relevant ones. "
            "Set sufficient_evidence=false if you believe another search round would help."
        )
        return self._call(prompt, EvidenceSelectionBatch)  # type: ignore[return-value]

    def decide_next_query(self, claim_or_question: str, evidence_so_far_count: int, round_number: int) -> NextQuery:
        prompt = (
            f"Claim or question: {claim_or_question!r}\n"
            f"Evidence sentences found so far: {evidence_so_far_count}\n"
            f"Search round: {round_number}\n\n"
            "Decide whether another PubMed search round is warranted, and if so, "
            "propose new_terms distinct from what was likely already tried."
        )
        return self._call(prompt, NextQuery)  # type: ignore[return-value]
