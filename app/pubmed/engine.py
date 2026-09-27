from __future__ import annotations

from app.pubmed.eutils import EUtilsClient
from app.pubmed.models import Paper
from app.pubmed.pmc_oa import PmcOaClient


class PubMedEngine:
    """search(term) -> [Paper, ...] with full text attached when the PMC
    Open Access Subset has it, abstract-only otherwise."""

    def __init__(self, email: str, api_key: str | None = None, try_full_text: bool = True):
        self.eutils = EUtilsClient(email=email, api_key=api_key)
        self.pmc = PmcOaClient(email=email) if try_full_text else None

    def search(self, term: str, retmax: int = 10) -> list[Paper]:
        pmids = self.eutils.esearch(term, retmax=retmax)
        papers = self.eutils.efetch_papers(pmids)
        if self.pmc:
            papers = [self.pmc.enrich(p) for p in papers]
        return papers

    def close(self) -> None:
        self.eutils.close()
        if self.pmc:
            self.pmc.close()
