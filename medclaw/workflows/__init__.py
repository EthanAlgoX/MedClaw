"""Core medical research workflows."""

from medclaw.workflows.clinical_trial_landscape import ClinicalTrialLandscapeWorkflow
from medclaw.workflows.drug_target_landscape import DrugTargetLandscapeWorkflow
from medclaw.workflows.evidence_brief import EvidenceBriefWorkflow
from medclaw.workflows.literature_review import LiteratureReviewWorkflow
from medclaw.workflows.study_design import StudyDesignWorkflow

__all__ = [
    "ClinicalTrialLandscapeWorkflow",
    "DrugTargetLandscapeWorkflow",
    "EvidenceBriefWorkflow",
    "LiteratureReviewWorkflow",
    "StudyDesignWorkflow",
]
