"""Workflow registry for typed medical research workflows."""

from __future__ import annotations

from medclaw.workflows import (
    ClinicalTrialLandscapeWorkflow,
    DrugTargetLandscapeWorkflow,
    EvidenceBriefWorkflow,
    LiteratureReviewWorkflow,
    StudyDesignWorkflow,
)


class WorkflowRegistry:
    """Central registry for MedClaw's typed research workflows."""

    def __init__(self):
        self.workflows = {
            "literature_review": LiteratureReviewWorkflow(),
            "clinical_trial_landscape": ClinicalTrialLandscapeWorkflow(),
            "drug_target_landscape": DrugTargetLandscapeWorkflow(),
            "study_design": StudyDesignWorkflow(),
            "evidence_brief": EvidenceBriefWorkflow(),
        }

    def get(self, workflow_id: str):
        """Return a workflow by id."""
        return self.workflows[workflow_id]

    def list_workflows(self) -> list[dict[str, str]]:
        """List available workflow ids and titles."""
        return [
            {
                "id": workflow_id,
                "title": workflow.title,
            }
            for workflow_id, workflow in self.workflows.items()
        ]

    def filter_valid_workflow_ids(self, workflow_ids: list[str]) -> list[str]:
        """Keep only workflow ids that exist in the registry."""
        return [workflow_id for workflow_id in workflow_ids if workflow_id in self.workflows]
