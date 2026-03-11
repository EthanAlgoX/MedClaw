"""Unit tests for medical research use cases."""

import asyncio
from pathlib import Path

from medclaw.application.use_cases import MedicalResearchUseCases
from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport
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


class CaptureProvider(LLMProvider):
    """Provider that records prompt messages for assertions."""

    def __init__(self):
        self.messages = None

    async def chat(self, messages, temperature=None, max_tokens=None, **kwargs) -> str:
        self.messages = messages
        return "Captured collection-aware summary."

    async def chat_with_tools(self, messages, tools=None, temperature=None, max_tokens=None, **kwargs):
        self.messages = messages
        return "Captured collection-aware summary.", []

    def get_default_model(self) -> str:
        return "capture-model"

    def get_available_models(self) -> list[str]:
        return ["capture-model"]


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


def test_run_workflow_report_injects_collection_manifest_context(temp_workspace: Path, monkeypatch):
    """Collection manifests should enrich report metadata and LLM synthesis context."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="KRAS Program",
        objective="Track resistance mechanisms and biomarker evidence",
        disease_area="Oncology",
        owner="Translational Team",
        tags=["kras", "oncology"],
        preferred_workflows=["literature_review", "evidence_brief"],
    )

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
    provider = CaptureProvider()

    report = asyncio.run(
        use_cases.run_workflow_report(
            workflow_id="literature_review",
            query="KRAS inhibitors",
            provider=provider,
            collection="KRAS Program",
        )
    )

    saved_report = use_cases.orchestrator.evidence_store.load_report(report.metadata["saved_path"])

    assert report.metadata["collection"] == "KRAS Program"
    assert report.metadata["collection_objective"] == "Track resistance mechanisms and biomarker evidence"
    assert report.metadata["collection_preferred_workflows"] == ["literature_review", "evidence_brief"]
    assert saved_report.metadata["collection_slug"] == "kras-program"
    assert provider.messages is not None
    assert "Collection: KRAS Program" in provider.messages[1]["content"]
    assert "Track resistance mechanisms and biomarker evidence" in provider.messages[1]["content"]


def test_run_workflow_report_without_llm_mentions_collection_context(temp_workspace: Path, monkeypatch):
    """Fallback summaries should preserve collection context when manifests exist."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="EGFR Program",
        objective="Track EGFR biomarker evidence",
    )

    async def fake_search(query: str, max_results: int = 8):
        return []

    monkeypatch.setattr(
        use_cases.orchestrator.workflows["literature_review"].gateway,
        "search",
        fake_search,
    )

    report = asyncio.run(
        use_cases.run_workflow_report(
            workflow_id="literature_review",
            query="EGFR biomarkers",
            provider=None,
            collection="EGFR Program",
        )
    )

    assert "for collection 'EGFR Program'" in report.summary
    assert "objective: Track EGFR biomarker evidence" in report.summary
    assert report.metadata["collection"] == "EGFR Program"


def test_run_collection_reports_prefers_collection_workflows(temp_workspace: Path, monkeypatch):
    """Collection-driven runs should select the first preferred workflow by default."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="KRAS Program",
        preferred_workflows=["study_design", "evidence_brief"],
    )

    async def fake_run(workflow_id: str, query: str, provider, collection: str | None = None):
        return ResearchReport(
            workflow_id=workflow_id,
            question=query,
            title=f"Stub: {workflow_id}",
            summary="Summary",
            metadata={"collection": collection or ""},
        )

    monkeypatch.setattr(use_cases.orchestrator, "run", fake_run)

    reports = asyncio.run(
        use_cases.run_collection_reports(
            query="KRAS inhibitors",
            provider=None,
            collection="KRAS Program",
        )
    )

    assert len(reports) == 1
    assert reports[0].workflow_id == "study_design"
    assert reports[0].metadata["collection"] == "KRAS Program"


def test_run_collection_reports_can_execute_all_preferred_workflows(temp_workspace: Path, monkeypatch):
    """Collection-driven runs should support batch execution of preferred workflows."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="EGFR Program",
        preferred_workflows=["study_design", "evidence_brief"],
    )

    async def fake_run(workflow_id: str, query: str, provider, collection: str | None = None):
        return ResearchReport(
            workflow_id=workflow_id,
            question=query,
            title=f"Stub: {workflow_id}",
            summary="Summary",
            metadata={"collection": collection or ""},
        )

    monkeypatch.setattr(use_cases.orchestrator, "run", fake_run)

    reports = asyncio.run(
        use_cases.run_collection_reports(
            query="EGFR biomarkers",
            provider=None,
            collection="EGFR Program",
            all_preferred=True,
        )
    )

    assert [report.workflow_id for report in reports] == ["study_design", "evidence_brief"]


def test_run_collection_reports_can_persist_bundle_artifacts(temp_workspace: Path, monkeypatch):
    """Collection-driven batch runs should persist a bundle summary artifact."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="EGFR Program",
        preferred_workflows=["study_design", "evidence_brief"],
    )

    async def fake_run(workflow_id: str, query: str, provider, collection: str | None = None):
        return ResearchReport(
            workflow_id=workflow_id,
            question=query,
            title=f"Stub: {workflow_id}",
            summary="Summary",
            metadata={
                "collection": collection or "",
                "saved_path": str(temp_workspace / f"{workflow_id}.json"),
            },
        )

    monkeypatch.setattr(use_cases.orchestrator, "run", fake_run)

    reports = asyncio.run(
        use_cases.run_collection_reports(
            query="EGFR biomarkers",
            provider=None,
            collection="EGFR Program",
            all_preferred=True,
            persist_bundle=True,
        )
    )

    assert len(reports) == 2
    assert reports[0].metadata["bundle_saved_path"].endswith("bundle_summary.md")
    assert reports[0].metadata["bundle_artifact_paths"]["bundle_json"].endswith("bundle_summary.json")


def test_run_collection_reports_can_override_collection_preference(temp_workspace: Path, monkeypatch):
    """Explicit workflow selection should override collection preferences."""
    use_cases = MedicalResearchUseCases(temp_workspace)
    use_cases.orchestrator.evidence_store.save_collection_manifest(
        name="EGFR Program",
        preferred_workflows=["study_design", "evidence_brief"],
    )

    async def fake_run(workflow_id: str, query: str, provider, collection: str | None = None):
        return ResearchReport(
            workflow_id=workflow_id,
            question=query,
            title=f"Stub: {workflow_id}",
            summary="Summary",
            metadata={"collection": collection or ""},
        )

    monkeypatch.setattr(use_cases.orchestrator, "run", fake_run)

    reports = asyncio.run(
        use_cases.run_collection_reports(
            query="EGFR biomarkers",
            provider=None,
            collection="EGFR Program",
            workflow_id="literature_review",
        )
    )

    assert len(reports) == 1
    assert reports[0].workflow_id == "literature_review"
