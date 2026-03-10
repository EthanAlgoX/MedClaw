"""Unit tests for medical domain facades."""

import asyncio

from medclaw.domain.medical.services import ClinicalTrialService, LiteratureService
from medclaw.evidence.models import EvidenceItem


def test_literature_service_uses_gateway_raw_and_evidence(monkeypatch):
    """The literature facade should expose both raw and normalized access."""
    service = LiteratureService()

    async def fake_search_raw(query: str, max_results: int = 20):
        return [{"pmid": "1", "title": "Paper 1"}]

    async def fake_search(query: str, max_results: int = 8):
        return [
            EvidenceItem(
                id="1",
                kind="literature",
                source="pubmed",
                title="Paper 1",
            )
        ]

    monkeypatch.setattr(service.gateway, "search_raw", fake_search_raw)
    monkeypatch.setattr(service.gateway, "search", fake_search)

    raw = asyncio.run(service.search("paper"))
    normalized = asyncio.run(service.search_evidence("paper"))

    assert raw[0]["pmid"] == "1"
    assert normalized[0].kind == "literature"


def test_clinical_trial_service_uses_gateway_raw_and_evidence(monkeypatch):
    """The clinical trial facade should expose both raw and normalized access."""
    service = ClinicalTrialService()

    async def fake_search_raw(query: str, max_results: int = 20):
        return [{"protocolSection": {"identificationModule": {"nctId": "NCT1"}}}]

    async def fake_search(query: str, max_results: int = 8):
        return [
            EvidenceItem(
                id="NCT1",
                kind="clinical_trial",
                source="clinicaltrials",
                title="Trial 1",
            )
        ]

    monkeypatch.setattr(service.gateway, "search_raw", fake_search_raw)
    monkeypatch.setattr(service.gateway, "search", fake_search)

    raw = asyncio.run(service.search("trial"))
    normalized = asyncio.run(service.search_evidence("trial"))

    assert raw[0]["protocolSection"]["identificationModule"]["nctId"] == "NCT1"
    assert normalized[0].kind == "clinical_trial"
