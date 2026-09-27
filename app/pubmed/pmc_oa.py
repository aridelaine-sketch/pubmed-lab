"""
PMC Open Access layer: PMID -> PMCID -> full text (when legally available).

- PMC ID Converter maps PMID to PMCID (not every PubMed article is in PMC).
- BioC API returns machine-readable full text ONLY for articles in the
  PMC Open Access Subset / Author Manuscript Collection. Most PMC
  articles are NOT in this subset, so "no full text" is the expected,
  normal outcome most of the time, not an error.

When full text is unavailable, the caller falls back to the abstract
already fetched via eutils.EUtilsClient.efetch_papers -- this fallback
is the explicit, required behaviour, never a silent failure.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.pubmed.models import Paper
from app.pubmed.rate_limit import RateLimiter

ID_CONVERTER = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
BIOC_BASE = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"


class PmcOaClient:
    def __init__(self, email: str, tool: str = "pubmed-lab", timeout: float = 20.0):
        self.email = email
        self.tool = tool
        self._limiter = RateLimiter(3.0)  # shares NCBI's general etiquette limit
        self._client = httpx.Client(timeout=timeout)

    def pmid_to_pmcid(self, pmids: list[str]) -> dict[str, str]:
        """Returns {pmid: pmcid} only for PMIDs that ARE in PMC."""
        if not pmids:
            return {}
        self._limiter.wait()
        resp = self._client.get(ID_CONVERTER, params={
            "ids": ",".join(pmids), "tool": self.tool, "email": self.email, "format": "json",
        })
        resp.raise_for_status()
        out = {}
        for rec in resp.json().get("records", []):
            if "pmcid" in rec and "pmid" in rec:
                out[rec["pmid"]] = rec["pmcid"]
        return out

    def fetch_full_text_bioc(self, pmid: str) -> dict[str, str] | None:
        """Returns {section_name: text} or None if not in the OA subset."""
        self._limiter.wait()
        url = f"{BIOC_BASE}/BioC_xml/{pmid}/unicode"
        resp = self._client.get(url)
        if resp.status_code != 200 or not resp.text.strip():
            return None
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return None
        sections: dict[str, str] = {}
        for passage in root.findall(".//passage"):
            section_type = "Body"
            for infon in passage.findall("./infon"):
                if infon.get("key") == "section_type":
                    section_type = infon.text or "Body"
            text_el = passage.find("./text")
            if text_el is not None and text_el.text:
                sections.setdefault(section_type, "")
                sections[section_type] += (" " + text_el.text)
        return sections or None

    def enrich(self, paper: Paper) -> Paper:
        """Attempts to attach full text to a Paper already populated from eutils."""
        pmcid_map = self.pmid_to_pmcid([paper.pmid])
        pmcid = pmcid_map.get(paper.pmid)
        if not pmcid:
            paper.has_full_text = False
            return paper
        paper.pmcid = pmcid
        sections = self.fetch_full_text_bioc(paper.pmid)
        if sections:
            paper.full_text_sections = sections
            paper.has_full_text = True
        else:
            paper.has_full_text = False
        return paper

    def close(self) -> None:
        self._client.close()
