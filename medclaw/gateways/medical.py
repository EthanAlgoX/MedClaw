"""Gateway adapters that access and normalize medical sources."""

from __future__ import annotations

from typing import Any

import httpx

from medclaw.evidence.models import Citation, EvidenceItem
from medclaw.gateways.cache import SimpleTTLCache


class PubMedGateway:
    """Gateway for PubMed search and fetch."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        cache_ttl_seconds: int = 300,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.cache = SimpleTTLCache(cache_ttl_seconds)

    async def search_raw(self, query: str, max_results: int = 8) -> list[dict[str, Any]]:
        """Return raw PubMed summary records."""
        cache_key = f"pubmed:search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            }
            if self.api_key:
                params["api_key"] = self.api_key

            search_response = await client.get(f"{self.base_url}/esearch.fcgi", params=params)
            search_response.raise_for_status()
            search_data = search_response.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return self.cache.set(cache_key, [])

            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list[:max_results]),
                "retmode": "json",
            }
            if self.api_key:
                summary_params["api_key"] = self.api_key

            summary_response = await client.get(
                f"{self.base_url}/esummary.fcgi",
                params=summary_params,
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()

        articles: list[dict[str, Any]] = []
        for pmid in id_list[:max_results]:
            if pmid in summary_data.get("result", {}):
                articles.append({"pmid": pmid, **summary_data["result"][pmid]})
        return self.cache.set(cache_key, articles)

    async def get_article_xml(self, pmid: str) -> dict[str, Any]:
        """Fetch full PubMed record XML."""
        cache_key = f"pubmed:article:{pmid}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
            if self.api_key:
                params["api_key"] = self.api_key
            response = await client.get(f"{self.base_url}/efetch.fcgi", params=params)
            response.raise_for_status()
        return self.cache.set(cache_key, {"pmid": pmid, "xml": response.text})

    async def search(self, query: str, max_results: int = 8) -> list[EvidenceItem]:
        """Return normalized literature evidence items."""
        articles = await self.search_raw(query, max_results=max_results)
        items: list[EvidenceItem] = []
        for article in articles:
            pmid = str(article.get("pmid", ""))
            title = str(article.get("title") or article.get("sorttitle") or "Untitled article")
            pubdate = article.get("pubdate")
            items.append(
                EvidenceItem(
                    id=pmid or title,
                    kind="literature",
                    source="pubmed",
                    title=title,
                    summary=str(article.get("elocationid") or article.get("source") or ""),
                    citations=[
                        Citation(
                            source="pubmed",
                            title=title,
                            identifier=pmid or None,
                            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
                            published_at=str(pubdate) if pubdate else None,
                        )
                    ],
                    metadata={
                        "authors": article.get("authors", []),
                        "journal": article.get("fulljournalname"),
                        "pubdate": pubdate,
                        "raw": article,
                    },
                )
            )
        return items


class ClinicalTrialsGateway:
    """Gateway for ClinicalTrials.gov search."""

    def __init__(
        self,
        base_url: str = "https://clinicaltrials.gov/api/v2",
        cache_ttl_seconds: int = 300,
    ):
        self.base_url = base_url
        self.cache = SimpleTTLCache(cache_ttl_seconds)

    async def search_raw(self, query: str, max_results: int = 8) -> list[dict[str, Any]]:
        """Return raw ClinicalTrials.gov study records."""
        cache_key = f"clinicaltrials:search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/studies",
                params={"query.term": query, "pageSize": max_results, "format": "json"},
            )
            response.raise_for_status()
            studies = response.json().get("studies", [])
        return self.cache.set(cache_key, studies)

    async def search(self, query: str, max_results: int = 8) -> list[EvidenceItem]:
        """Return normalized clinical trial evidence items."""
        trials = await self.search_raw(query, max_results=max_results)
        items: list[EvidenceItem] = []
        for trial in trials:
            protocol = trial.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            nct_id = str(identification.get("nctId", ""))
            title = str(
                identification.get("briefTitle")
                or identification.get("officialTitle")
                or "Untitled trial"
            )
            status = str(status_module.get("overallStatus", "unknown"))
            items.append(
                EvidenceItem(
                    id=nct_id or title,
                    kind="clinical_trial",
                    source="clinicaltrials",
                    title=title,
                    summary=f"Status: {status}",
                    citations=[
                        Citation(
                            source="clinicaltrials.gov",
                            title=title,
                            identifier=nct_id or None,
                            url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None,
                        )
                    ],
                    metadata={"status": status, "nct_id": nct_id, "raw": trial},
                )
            )
        return items


class DrugGateway:
    """Gateway for drug lookup and interaction data."""

    def __init__(self, source: str = "drugbank"):
        self.source = source

    async def search_raw(self, query: str) -> dict[str, Any]:
        """Return raw drug lookup data."""
        return {"name": query, "source": self.source, "status": "not_implemented"}

    async def search(self, query: str) -> list[EvidenceItem]:
        """Return normalized drug evidence items."""
        result = await self.search_raw(query)
        return [
            EvidenceItem(
                id=str(result.get("name", query)),
                kind="drug",
                source=str(result.get("source", "drug-service")),
                title=str(result.get("name", query)),
                summary=str(result.get("status", "")),
                metadata=result,
            )
        ]

    async def check_interaction_raw(self, drug1: str, drug2: str) -> dict[str, Any]:
        """Return raw drug interaction data."""
        return {"drug1": drug1, "drug2": drug2, "interaction": "not_implemented"}

    async def check_interaction(self, drug1: str, drug2: str) -> EvidenceItem:
        """Return normalized interaction evidence."""
        result = await self.check_interaction_raw(drug1, drug2)
        return EvidenceItem(
            id=f"{drug1}:{drug2}",
            kind="drug_interaction",
            source="drug-service",
            title=f"{drug1} / {drug2}",
            summary=str(result.get("interaction", "")),
            metadata=result,
        )


class GuidelinesGateway:
    """Gateway for guideline search."""

    def __init__(self):
        self.source = "NICE/CDC/WHO"

    async def search_raw(self, condition: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Return raw guideline search results."""
        return [
            {
                "condition": condition,
                "guideline": "not_implemented",
                "source": self.source,
            }
            for _ in range(min(max_results, 1))
        ]

    async def search(self, condition: str, max_results: int = 5) -> list[EvidenceItem]:
        """Return normalized guideline evidence items."""
        guidelines = await self.search_raw(condition, max_results=max_results)
        items: list[EvidenceItem] = []
        for idx, guideline in enumerate(guidelines):
            title = str(guideline.get("guideline", "Guideline summary"))
            items.append(
                EvidenceItem(
                    id=f"guideline-{idx}",
                    kind="guideline",
                    source=str(guideline.get("source", "guideline-service")),
                    title=title,
                    summary=str(guideline.get("condition", condition)),
                    metadata=guideline,
                )
            )
        return items
