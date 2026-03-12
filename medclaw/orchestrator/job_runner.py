"""Compatibility facade over the decomposed research orchestration services."""

from __future__ import annotations

from pathlib import Path

from medclaw.evidence.models import ResearchReport
from medclaw.evidence.store import EvidenceStore
from medclaw.orchestrator.collection_service import CollectionService
from medclaw.orchestrator.report_persistence import ReportPersistenceService
from medclaw.orchestrator.run_coordinator import RunCoordinator
from medclaw.orchestrator.workflow_registry import WorkflowRegistry
from medclaw.policy.medical_safety import MedicalSafetyPolicy
from medclaw.providers.base import LLMProvider


class ResearchOrchestrator:
    """Compatibility facade exposing the previous orchestrator API."""

    def __init__(self, workspace: Path):
        self.evidence_store = EvidenceStore(workspace)
        self.policy = MedicalSafetyPolicy()
        self.workflow_registry = WorkflowRegistry()
        self.collection_service = CollectionService(self.evidence_store, self.workflow_registry)
        self.report_persistence = ReportPersistenceService(self.evidence_store)
        self.run_coordinator = RunCoordinator(
            self.workflow_registry,
            self.collection_service,
            self.report_persistence,
            policy=self.policy,
        )
        self.workflows = self.workflow_registry.workflows

    async def run(
        self,
        workflow_id: str,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
    ):
        """Run a workflow through the decomposed coordinator stack."""
        return await self.run_coordinator.run(
            workflow_id,
            query,
            provider,
            collection=collection,
        )

    def render(self, report: ResearchReport) -> str:
        """Render a workflow report into markdown."""
        return self.run_coordinator.render(report)

    def list_workflows(self) -> list[dict[str, str]]:
        """List available workflow ids and titles."""
        return self.workflow_registry.list_workflows()

    def resolve_collection_workflows(self, collection: str | None) -> list[str]:
        """Resolve preferred workflows for a collection, keeping only valid ids."""
        return self.collection_service.resolve_workflows(collection)

    def save_collection_bundle(self, reports: list[ResearchReport]) -> dict[str, Path]:
        """Persist a collection-level synthesis bundle across multiple workflow reports."""
        return self.report_persistence.save_collection_bundle(reports)

    def _resolve_collection_context(self, collection: str | None) -> dict[str, object] | None:
        """Load saved collection context when available and preserve ad-hoc collection names."""
        return self.collection_service.resolve_context(collection)
