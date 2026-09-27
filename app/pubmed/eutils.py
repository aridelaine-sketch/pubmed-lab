"""
NCBI E-utilities client.

Implements the standard, documented pattern:

    esearch  -> PMIDs matching a PubMed-syntax query
    efetch   -> full PubMed XML records (title, abstract, authors,
                journal, year, DOI) for those PMIDs

Rate limits (NCBI usage policy): 3 requests/second without an API key,
10 requests/second with one. `tool` and `email` are sent on every
request as NCBI's usage policy asks. This module makes real network
calls to https://eutils.ncbi.nlm.nih.gov — it needs outbound internet
access, which a sandboxed environment may not have (see demo/ for an
offline fixture-based walkthrough of everything downstream of this
module).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.pubmed.models import Paper
from app.pubmed.rate_limit import RateLimiter

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class EUtilsClient:
    def __init__(self, email: str, tool: str = "pubmed-lab", api_key: str | None = None, timeout: float = 20.0):
        self.email = email
        self.tool = tool
        self.api_key = api_key
        self.timeout = timeout
        self._limiter = RateLimiter(10.0 if api_key else 3.0)
        self._client = httpx.Client(timeout=timeout)

    def _params(self, **extra) -> dict:
        p = {"tool": self.tool, "email": self.email, **extra}
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    def _get(self, path: str, **params) -> httpx.Response:
        self._limiter.wait()
        resp = self._client.get(f"{BASE}/{path}", params=self._params(**params))
        resp.raise_for_status()
        return resp

    def esearch(self, term: str, retmax: int = 20) -> list[str]:
        """PubMed-syntax query -> list of PMIDs."""
        resp = self._get("esearch.fcgi", db="pubmed", term=term, retmode="json", retmax=retmax)
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def efetch_papers(self, pmids: list[str]) -> list[Paper]:
        """PMIDs -> parsed Paper objects (title, abstract, authors, journal, year, DOI)."""
        if not pmids:
            return []
        resp = self._get("efetch.fcgi", db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml")
        return self._parse_pubmed_xml(resp.text)

    @staticmethod
    def _parse_pubmed_xml(xml_text: str) -> list[Paper]:
        root = ET.fromstring(xml_text)
        papers: list[Paper] = []
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("./MedlineCitation")
            pmid_el = medline.find("./PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            article_el = medline.find("./Article")
            title_el = article_el.find("./ArticleTitle") if article_el is not None else None
            title = "".join(title_el.itertext()).strip() if title_el is not None else ""

            abstract_parts = []
            if article_el is not None:
                for ab in article_el.findall("./Abstract/AbstractText"):
                    label = ab.get("Label")
                    text = "".join(ab.itertext()).strip()
                    abstract_parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(abstract_parts)

            journal_el = article_el.find("./Journal/Title") if article_el is not None else None
            journal = journal_el.text if journal_el is not None else ""

            year_el = article_el.find("./Journal/JournalIssue/PubDate/Year") if article_el is not None else None
            year = year_el.text if year_el is not None else ""

            authors = []
            if article_el is not None:
                for a in article_el.findall("./AuthorList/Author"):
                    last = a.find("./LastName")
                    initials = a.find("./Initials")
                    if last is not None:
                        name = last.text + (f" {initials.text}" if initials is not None else "")
                        authors.append(name)

            doi = ""
            for idn in article.findall(".//ArticleId"):
                if idn.get("IdType") == "doi":
                    doi = idn.text or ""

            papers.append(Paper(
                pmid=pmid, title=title, journal=journal or "", year=year or "",
                authors=authors, doi=doi, abstract=abstract,
            ))
        return papers

    def close(self) -> None:
        self._client.close()
