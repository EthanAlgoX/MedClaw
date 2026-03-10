"""Gateway adapters that normalize medical source responses."""

from __future__ import annotations

from typing import Any

from medclaw.domain.medical.services import (
    ClinicalTrialService,
    DrugService,
    GuidelineService,
    LiteratureService,
)
from medclaw.evidence.models import Citation, EvidenceItem


class PubMedGateway:
    """Gateway for PubMed-style literature search."""

    def __init__(self, service: LiteratureService | None = None):
        self.service = service or LiteratureService()

    async def search(self, query: str, max_results: int = 8) -> list[EvidenceItem]:
        articles = await self.service.search(query, max_results=max_results)
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
                    },
                )
            )
        return items


class ClinicalTrialsGateway:
    """Gateway for ClinicalTrials.gov search."""

    def __init__(self, service: ClinicalTrialService | None = None):
        self.service = service or ClinicalTrialService()

    async def search(self, query: str, max_results: int = 8) -> list[EvidenceItem]:
        trials = await self.service.search(query, max_results=max_results)
        items: list[EvidenceItem] = []
        for trial in trials:
            protocol = trial.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            nct_id = str(identification.get("nctId", ""))
            title = str(identification.get("briefTitle") or identification.get("officialTitle") or "Untitled trial")
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
                    metadata={
                        "status": status,
                        "nct_id": nct_id,
                        "raw": trial,
                    },
                )
            )
        return items


class DrugGateway:
    """Gateway for drug lookup and interaction data."""

    def __init__(self, service: DrugService | None = None):
        self.service = service or DrugService()

    async def search(self, query: str) -> list[EvidenceItem]:
        result = await self.service.search(query)
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

    async def check_interaction(self, drug1: str, drug2: str) -> EvidenceItem:
        result = await self.service.check_interaction(drug1, drug2)
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

    def __init__(self, service: GuidelineService | None = None):
        self.service = service or GuidelineService()

    async def search(self, condition: str, max_results: int = 5) -> list[EvidenceItem]:
        guidelines = await self.service.search(condition, max_results=max_results)
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
