from __future__ import annotations

import datetime
import re
from pathlib import Path

from app.decision_model.schemas import Relation
from app.evidence.provenance import Evidence


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", s)[:60]


def _source_block(ev: Evidence) -> str:
    lines = [
        f"> {ev.sentence}",
        "",
        f"**Source:** {ev.first_author_et_al}, {ev.journal}, {ev.year}  ",
        f"**PMID:** {ev.pmid}  ",
    ]
    if ev.doi:
        lines.append(f"**DOI:** {ev.doi}  ")
    if ev.source_type == "full_text":
        lines.append(f"**Section:** {ev.section} (full text)  ")
    else:
        lines.append("**Section:** Abstract  ")
    return "\n".join(lines)


def _frontmatter(topic: str, note_type: str, tags: list[str]) -> str:
    today = datetime.date.today().isoformat()
    tag_str = ", ".join(tags)
    return (
        "---\n"
        f"type: {note_type}\n"
        f"topic: {topic}\n"
        f"created: {today}\n"
        f"tags: [{tag_str}]\n"
        "---\n"
    )


def _references(evidence: list[Evidence]) -> str:
    seen = {}
    for e in evidence:
        seen[e.pmid] = e
    lines = ["## References", ""]
    for pmid, e in seen.items():
        lines.append(f"- PMID: {pmid} — {e.first_author_et_al}, {e.journal}, {e.year}")
    return "\n".join(lines)


def render_learn(topic: str, sections: dict[str, list[Evidence]], category: str) -> str:
    """sections: ordered dict of section_title -> list[Evidence] (support only,
    with an optional 'Evidence against / limitations' subsection handled by
    the caller passing relation-tagged evidence)."""
    out = [_frontmatter(topic, "learning-note", [_slug(category), "evidence-based"]), ""]
    out.append(f"# {topic}\n")

    all_evidence: list[Evidence] = []
    for i, (section_title, ev_list) in enumerate(sections.items(), start=1):
        out.append(f"## {i}. {section_title}\n")
        supporting = [e for e in ev_list if e.relation == Relation.SUPPORT]
        qualifying = [e for e in ev_list if e.relation in (Relation.CONTRADICT, Relation.QUALIFY)]

        if not supporting and not qualifying:
            out.append("*Insufficient evidence found.*\n")
        for e in supporting:
            out.append(_source_block(e) + "\n")
        if qualifying:
            out.append("### Evidence against / limitations\n")
            for e in qualifying:
                out.append(_source_block(e) + "\n")
        out.append("---\n")
        all_evidence.extend(ev_list)

    out.append(_references(all_evidence))
    return "\n".join(out)


def render_question(question: str, category: str, evidence: list[Evidence]) -> str:
    out = [_frontmatter(question[:60], "question-note", [_slug(category)]), ""]
    out.append("## Question\n")
    out.append(f"{question}\n")
    out.append("## Evidence\n")
    if not evidence:
        out.append("*Insufficient evidence found.*\n")
    for e in evidence:
        out.append(_source_block(e) + "\n")
    out.append(_references(evidence))
    return "\n".join(out)


def render_claim(claim: str, category: str, evidence: list[Evidence]) -> str:
    out = [_frontmatter(claim[:60], "claim-note", [_slug(category)]), ""]
    out.append("## Claim\n")
    out.append(f"{claim}\n")

    supporting = [e for e in evidence if e.relation == Relation.SUPPORT]
    contradicting = [e for e in evidence if e.relation in (Relation.CONTRADICT, Relation.QUALIFY)]

    out.append("## Supporting evidence\n")
    if not supporting:
        out.append("*Insufficient evidence found.*\n")
    for e in supporting:
        out.append(_source_block(e) + "\n")

    out.append("## Contradicting / qualifying evidence\n")
    if not contradicting:
        out.append("*No contradicting or qualifying evidence found.*\n")
    for e in contradicting:
        out.append(_source_block(e) + "\n")

    out.append(_references(evidence))
    return "\n".join(out)


def save_to_vault(markdown: str, vault_path: str | Path, topic: str) -> Path:
    vault_path = Path(vault_path)
    vault_path.mkdir(parents=True, exist_ok=True)
    file_path = vault_path / f"{_slug(topic)}.md"
    file_path.write_text(markdown, encoding="utf-8")
    return file_path
