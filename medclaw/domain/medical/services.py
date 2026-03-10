"""Medical domain facades built on top of the gateway layer."""

from __future__ import annotations

from typing import Any

from medclaw.gateways.medical import (
    ClinicalTrialsGateway,
    DrugGateway,
    GuidelinesGateway,
    PubMedGateway,
)


class LiteratureService:
    """Compatibility facade for literature retrieval."""

    def __init__(self, api_key: str | None = None, gateway: PubMedGateway | None = None):
        self.gateway = gateway or PubMedGateway(api_key=api_key)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Return raw article summaries for compatibility with existing tools/tests."""
        return await self.gateway.search_raw(query, max_results=max_results)

    async def search_evidence(
        self,
        query: str,
        max_results: int = 8,
    ):
        """Return normalized evidence items for workflow consumers."""
        return await self.gateway.search(query, max_results=max_results)

    async def get_article(self, pmid: str) -> dict[str, Any]:
        """Return raw article XML."""
        return await self.gateway.get_article_xml(pmid)


class ClinicalTrialService:
    """Compatibility facade for clinical trial search."""

    def __init__(self, gateway: ClinicalTrialsGateway | None = None):
        self.gateway = gateway or ClinicalTrialsGateway()

    async def search(
        self,
        query: str,
        max_results: int = 20,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Return raw study records."""
        return await self.gateway.search_raw(query, max_results=max_results)

    async def search_evidence(
        self,
        query: str,
        max_results: int = 8,
    ):
        """Return normalized clinical trial evidence."""
        return await self.gateway.search(query, max_results=max_results)


class DrugService:
    """Compatibility facade for drug data."""

    def __init__(self, source: str = "drugbank", gateway: DrugGateway | None = None):
        self.gateway = gateway or DrugGateway(source=source)

    async def search(self, drug_name: str) -> dict[str, Any]:
        """Return raw drug lookup result."""
        return await self.gateway.search_raw(drug_name)

    async def search_evidence(self, drug_name: str):
        """Return normalized drug evidence."""
        return await self.gateway.search(drug_name)

    async def check_interaction(self, drug1: str, drug2: str) -> dict[str, Any]:
        """Return raw interaction result."""
        return await self.gateway.check_interaction_raw(drug1, drug2)

    async def check_interaction_evidence(self, drug1: str, drug2: str):
        """Return normalized interaction evidence."""
        return await self.gateway.check_interaction(drug1, drug2)


class GuidelineService:
    """Compatibility facade for guideline data."""

    def __init__(self, gateway: GuidelinesGateway | None = None):
        self.gateway = gateway or GuidelinesGateway()

    async def search(
        self,
        condition: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Return raw guideline records."""
        return await self.gateway.search_raw(condition, max_results=max_results)

    async def search_evidence(
        self,
        condition: str,
        max_results: int = 5,
    ):
        """Return normalized guideline evidence."""
        return await self.gateway.search(condition, max_results=max_results)


class MedicalDomainPlugin:
    """Medical domain facade and runtime metadata."""

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.literature = LiteratureService(api_key=config.get("pubmedApiKey"))
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
            },
            "normalized_entities": [
                "literature",
                "clinical_trial",
                "drug",
                "guideline",
                "drug_interaction",
            ],
        }

    def get_source_health(self) -> dict[str, str]:
        """Return health status of data sources."""
        return {
            "pubmed": "ok",
            "clinicaltrials": "ok",
            "drugs": "ok",
            "guidelines": "ok",
        }
