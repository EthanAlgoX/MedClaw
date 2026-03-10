"""Unit tests for medical research use cases."""

import asyncio
from pathlib import Path

from medclaw.application.use_cases import MedicalResearchUseCases
from medclaw.evidence.models import Citation, EvidenceItem
from medclaw.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    """Minimal provider for testing workflow orchestration."""

    async def chat(self, messages, temperature=None, max_tokens=None, **kwargs) -> str:
        return "Synthetic research summary."

    async def chat_with_tools(self, messages, tools=None, temperature=None, max_tokens=None, **kwargs):
        return "Synthetic research summary.", []

    def get_default_model(self) -> str:
        return "fake-model"

    def get_available_models(self) -> list[str]:
        return ["fake-model"]


def test_use_case_runs_and_saves_report(temp_workspace: Path, monkeypatch):
    """Typed research queries should run through the new workflow stack."""
    use_cases = MedicalResearchUseCases(temp_workspace)

    async def fake_search(query: str, max_results: int = 8):
        return [
            EvidenceItem(
                id="1",
                kind="literature",
                source="pubmed",
                title="Paper 1",
                summary="Key paper",
                citations=[Citation(source="pubmed", title="Paper 1", identifier="1")],
            )
        ]

    monkeypatch.setattr(
        use_cases.orchestrator.workflows["literature_review"].gateway,
        "search",
        fake_search,
    )

    result = asyncio.run(
        use_cases.run_query(
            "Please do a literature review on KRAS inhibitors",
            FakeProvider(),
        )
    )

    assert result is not None
    assert "Literature Review" in result
    saved_reports = list((temp_workspace / "research" / "reports").glob("*.json"))
    assert saved_reports
