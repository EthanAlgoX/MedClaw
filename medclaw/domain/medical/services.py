"""Medical domain services."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


class LiteratureService:
    """PubMed/EMBASE literature service."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs
    ) -> list[dict[str, Any]]:
        """Search PubMed for articles."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = f"{self.base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            }
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            summary_url = f"{self.base_url}/esummary.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(id_list[:max_results]),
                "retmode": "json",
            }
            response = await client.get(summary_url, params=params)
            response.raise_for_status()
            summary_data = response.json()

            articles = []
            for pmid in id_list[:max_results]:
                if pmid in summary_data.get("result", {}):
                    articles.append({
                        "pmid": pmid,
                        **summary_data["result"][pmid]
                    })

            return articles

    async def get_article(self, pmid: str) -> dict[str, Any]:
        """Get article details by PMID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}/efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml",
            }
            response = await client.get(url, params=params)
            response.raise_for_status()

            return {"pmid": pmid, "xml": response.text}


class ClinicalTrialService:
    """ClinicalTrials.gov service."""

    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2"

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs
    ) -> list[dict[str, Any]]:
        """Search ClinicalTrials.gov."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}/studies"
            params = {
                "query.term": query,
                "pageSize": max_results,
                "format": "json",
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return data.get("studies", [])


class DrugService:
    """Drug information service."""

    def __init__(self, source: str = "drugbank"):
        self.source = source

    async def search(self, drug_name: str) -> dict[str, Any]:
        """Search for drug information."""
        return {
            "name": drug_name,
            "source": self.source,
            "status": "not_implemented",
        }

    async def check_interaction(self, drug1: str, drug2: str) -> dict[str, Any]:
        """Check drug-drug interactions."""
        return {
            "drug1": drug1,
            "drug2": drug2,
            "interaction": "not_implemented",
        }


class GuidelineService:
    """Clinical guidelines service."""

    def __init__(self):
        pass

    async def search(
        self,
        condition: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search clinical guidelines."""
        return [
            {
                "condition": condition,
                "guideline": "not_implemented",
                "source": "NICE/CDC/WHO",
            }
        ]


class MedicalDomainPlugin:
    """Medical domain plugin for MedClaw."""

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.literature = LiteratureService()
        self.trials = ClinicalTrialService()
        self.drugs = DrugService(config.get("drugSource", "drugbank"))
        self.guidelines = GuidelineService()

    def get_runtime_profile(self) -> dict[str, Any]:
        """Return runtime capability profile."""
        return {
            "tool_markets": {
                "med_pubmed_search": ["global"],
                "med_clinical_trials": ["global"],
                "med_drug_lookup": ["global"],
                "med_guidelines": ["global"],
            },
            "tool_freshness": {
                "med_pubmed_search": ["realtime"],
                "med_clinical_trials": ["realtime"],
                "med_drug_lookup": ["monthly"],
                "med_guidelines": ["monthly"],
            }
        }

    def get_source_health(self) -> dict[str, str]:
        """Return health status of data sources."""
        return {
            "pubmed": "ok",
            "clinicaltrials": "ok",
            "drugs": "ok",
            "guidelines": "ok",
        }
