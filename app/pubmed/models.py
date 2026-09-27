from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Paper:
    pmid: str
    title: str
    journal: str = ""
    year: str = ""
    authors: list[str] = field(default_factory=list)
    doi: str = ""
    pmcid: str | None = None
    abstract: str = ""
    full_text_sections: dict[str, str] = field(default_factory=dict)  # section -> text
    has_full_text: bool = False

    @property
    def first_author_et_al(self) -> str:
        if not self.authors:
            return "Unknown"
        return self.authors[0] + (" et al." if len(self.authors) > 1 else "")
