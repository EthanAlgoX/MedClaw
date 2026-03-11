"""Workflow execution for MedClaw research jobs."""

from __future__ import annotations

from pathlib import Path

from medclaw.evidence.models import ResearchReport
from medclaw.evidence.store import EvidenceStore
from medclaw.policy.medical_safety import MedicalSafetyPolicy
from medclaw.providers.base import LLMProvider
from medclaw.reporting.briefs import render_collection_report_bundle, render_research_report
from medclaw.workflows import (
    ClinicalTrialLandscapeWorkflow,
    DrugTargetLandscapeWorkflow,
    EvidenceBriefWorkflow,
    LiteratureReviewWorkflow,
    StudyDesignWorkflow,
)


class ResearchOrchestrator:
    """Run typed research workflows and persist their outputs."""

    def __init__(self, workspace: Path):
        self.evidence_store = EvidenceStore(workspace)
        self.policy = MedicalSafetyPolicy()
        self.workflows = {
            "literature_review": LiteratureReviewWorkflow(),
            "clinical_trial_landscape": ClinicalTrialLandscapeWorkflow(),
            "drug_target_landscape": DrugTargetLandscapeWorkflow(),
            "study_design": StudyDesignWorkflow(),
            "evidence_brief": EvidenceBriefWorkflow(),
        }

    async def run(
        self,
        workflow_id: str,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
    ) -> ResearchReport:
        """Run a workflow, attach policy, and persist the report."""
        workflow = self.workflows[workflow_id]
        collection_context = self._resolve_collection_context(collection)
        report = await workflow.run(query, provider, collection_context=collection_context)
        report = self.policy.apply(report)
        artifact_paths = self.evidence_store.save_report_artifacts(report)
        report.metadata["saved_path"] = str(artifact_paths["report"])
        report.metadata["artifact_dir"] = str(artifact_paths["artifact_dir"])
        report.metadata["artifact_paths"] = {
            name: str(path) for name, path in artifact_paths.items()
        }
        report.metadata["llm_enabled"] = provider is not None
        return report

    def render(self, report: ResearchReport) -> str:
        """Render a workflow report into markdown."""
        return render_research_report(report)

    def list_workflows(self) -> list[dict[str, str]]:
        """List available workflow ids and titles."""
        return [
            {
                "id": workflow_id,
                "title": workflow.title,
            }
            for workflow_id, workflow in self.workflows.items()
        ]

    def resolve_collection_workflows(self, collection: str | None) -> list[str]:
        """Resolve preferred workflows for a collection, keeping only valid ids."""
        collection_context = self._resolve_collection_context(collection)
        if not collection_context:
            return []

        preferred = collection_context.get("preferred_workflows", [])
        if not isinstance(preferred, list):
            return []
        return [workflow_id for workflow_id in preferred if workflow_id in self.workflows]

    def save_collection_bundle(self, reports: list[ResearchReport]) -> dict[str, Path]:
        """Persist a collection-level synthesis bundle across multiple workflow reports."""
        markdown_summary = render_collection_report_bundle(reports)
        return self.evidence_store.save_collection_bundle_artifacts(reports, markdown_summary)

    def _resolve_collection_context(self, collection: str | None) -> dict[str, object] | None:
        """Load saved collection context when available and preserve ad-hoc collection names."""
        if not collection or not collection.strip():
            return None

        normalized = collection.strip()
        try:
            return self.evidence_store.load_collection_manifest(normalized)
        except FileNotFoundError:
            return {"name": normalized}
