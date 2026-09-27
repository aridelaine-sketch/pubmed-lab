import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.decision_model.schemas import Relation
from app.evidence.provenance import Evidence
from app.export.markdown import render_claim, render_question
from app.pubmed.sentence_split import split_sentences


def make_evidence(sentence, relation, pmid="1"):
    return Evidence(
        sentence=sentence, relation=relation, confidence=0.9, pmid=pmid, pmcid=None,
        doi="10.1/x", journal="J", year="2021", first_author_et_al="Doe J",
        section="Abstract", source_type="abstract", sentence_index=0,
    )


def test_claim_note_splits_support_and_contradict_sections():
    evidence = [
        make_evidence("Supports the claim.", Relation.SUPPORT, pmid="1"),
        make_evidence("Contradicts the claim.", Relation.CONTRADICT, pmid="2"),
        make_evidence("Qualifies the claim.", Relation.QUALIFY, pmid="3"),
    ]
    md = render_claim("X is associated with Y.", "cardiology", evidence)

    support_idx = md.index("## Supporting evidence")
    contra_idx = md.index("## Contradicting / qualifying evidence")
    assert support_idx < contra_idx
    assert "Supports the claim." in md[support_idx:contra_idx]
    assert "Contradicts the claim." in md[contra_idx:]
    assert "Qualifies the claim." in md[contra_idx:]
    assert "Insufficient evidence found" not in md  # both sections have content


def test_question_note_shows_insufficient_evidence_marker_when_empty():
    md = render_question("Why does X happen?", "physiology", [])
    assert "*Insufficient evidence found.*" in md


def test_frontmatter_is_valid_obsidian_yaml_block():
    md = render_question("q", "cat", [])
    assert md.startswith("---\n")
    assert "type: question-note" in md
    assert md.count("---") >= 2


def test_sentence_splitter_does_not_split_on_abbreviation():
    text = "See Fig. 2 for details. The result was significant (P < .05)."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0].startswith("See Fig. 2 for details.")


def test_sentence_splitter_handles_et_al():
    text = "Smith et al. showed an effect. This was confirmed later."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "Smith et al. showed an effect." == sentences[0]
