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
    artifact_dirs = list((temp_workspace / "research" / "reports").glob("*_artifacts"))
    assert artifact_dirs


def test_use_case_lists_workflows(temp_workspace: Path):
    """Typed workflows should be discoverable from the application layer."""
    use_cases = MedicalResearchUseCases(temp_workspace)

    workflows = use_cases.list_workflows()
    workflow_ids = {workflow["id"] for workflow in workflows}

    assert "literature_review" in workflow_ids
    assert "clinical_trial_landscape" in workflow_ids
    assert "evidence_brief" in workflow_ids


def test_run_workflow_report_without_llm(temp_workspace: Path, monkeypatch):
    """Typed workflows should support deterministic fallback summaries without an LLM."""
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

    report = asyncio.run(
        use_cases.run_workflow_report(
            workflow_id="literature_review",
            query="KRAS inhibitors",
            provider=None,
        )
    )

    assert "without an LLM" in report.summary
    assert report.metadata["llm_enabled"] is False
    assert report.metadata["saved_path"]
    assert report.metadata["artifact_dir"]
    assert report.metadata["artifact_paths"]["citations"].endswith("citations.json")
