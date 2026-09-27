"""
A deliberately small, dependency-free sentence splitter.

Biomedical abstracts have enough quirks (e.g. "Fig. 2", "P < .001",
"vs.") that a naive split on '.' breaks often. This is not a full NLP
sentence tokenizer -- it's tuned to be conservative (prefer under- over
over-splitting) because a merged sentence is still safe to select from,
while a wrongly split one can misattribute meaning.
"""

from __future__ import annotations

import re

_ABBREVIATIONS = {"fig", "figs", "dr", "vs", "e.g", "i.e", "et al", "p", "no", "approx"}
_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    raw = _SPLIT_RE.split(text)

    merged: list[str] = []
    for piece in raw:
        if merged:
            prev = merged[-1]
            last_word = prev.rstrip(".").split(" ")[-1].lower()
            if last_word in _ABBREVIATIONS or len(prev.split()) < 3:
                merged[-1] = prev + " " + piece
                continue
        merged.append(piece)
    return [s.strip() for s in merged if s.strip()]
