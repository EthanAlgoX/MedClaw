"""Workflow execution for MedClaw research jobs."""

from __future__ import annotations

from pathlib import Path

from medclaw.evidence.models import ResearchReport
from medclaw.evidence.store import EvidenceStore
from medclaw.policy.medical_safety import MedicalSafetyPolicy
from medclaw.providers.base import LLMProvider
from medclaw.reporting.briefs import render_research_report
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
        report = await workflow.run(query, provider)
        report = self.policy.apply(report)
        if collection and collection.strip():
            report.metadata["collection"] = collection.strip()
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
