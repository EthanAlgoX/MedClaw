"""Workflow run coordination for MedClaw research jobs."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.policy.medical_safety import MedicalSafetyPolicy
from medclaw.providers.base import LLMProvider
from medclaw.reporting.briefs import render_research_report
from medclaw.orchestrator.collection_service import CollectionService
from medclaw.orchestrator.report_persistence import ReportPersistenceService
from medclaw.orchestrator.workflow_registry import WorkflowRegistry


class RunCoordinator:
    """Coordinate workflow execution, policy application, and report persistence."""

    def __init__(
        self,
        workflow_registry: WorkflowRegistry,
        collection_service: CollectionService,
        report_persistence: ReportPersistenceService,
        policy: MedicalSafetyPolicy | None = None,
    ):
        self.workflow_registry = workflow_registry
        self.collection_service = collection_service
        self.report_persistence = report_persistence
        self.policy = policy or MedicalSafetyPolicy()

    async def run(
        self,
        workflow_id: str,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
    ) -> ResearchReport:
        """Run a workflow, apply policy, and persist the report."""
        workflow = self.workflow_registry.get(workflow_id)
        collection_context = self.collection_service.resolve_context(collection)
        report = await workflow.run(query, provider, collection_context=collection_context)
        report = self.policy.apply(report)
        return self.report_persistence.persist_report(
            report,
            llm_enabled=provider is not None,
            provider_name=self._provider_name(provider),
            model_name=self._model_name(provider),
        )

    def render(self, report: ResearchReport) -> str:
        """Render a workflow report into markdown."""
        return render_research_report(report)

    def _provider_name(self, provider: LLMProvider | None) -> str:
        """Infer a stable provider label for run metadata."""
        if provider is None:
            return ""
        name = provider.__class__.__name__
        if name.endswith("Provider"):
            name = name[:-8]
        return name.lower()

    def _model_name(self, provider: LLMProvider | None) -> str:
        """Resolve the default model associated with the execution provider."""
        if provider is None:
            return ""
        try:
            return provider.get_default_model()
        except Exception:
            return ""
