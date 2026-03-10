"""Intent router for medical research workflows."""

from __future__ import annotations

import re


class ResearchRouter:
    """Map free-text queries onto core MedClaw workflows."""

    _RULES: dict[str, tuple[str, ...]] = {
        "clinical_trial_landscape": (
            "clinical trial",
            "clinicaltrials",
            "recruiting",
            "nct",
            "trial landscape",
            "trial matching",
        ),
        "study_design": (
            "study design",
            "sample size",
            "power analysis",
            "endpoint",
            "cohort design",
            "protocol design",
        ),
        "literature_review": (
            "literature review",
            "review the literature",
            "papers",
            "pubmed",
            "recent studies",
            "systematic review",
            "meta-analysis",
        ),
        "drug_target_landscape": (
            "drug target",
            "drug landscape",
            "target validation",
            "repurposing",
            "compound",
            "mechanism of action",
        ),
        "evidence_brief": (
            "evidence",
            "brief",
            "summary",
            "compare evidence",
            "what is known",
        ),
    }

    _MEDICAL_TERMS = {
        "cancer",
        "trial",
        "disease",
        "drug",
        "patient",
        "therapy",
        "clinical",
        "gene",
        "biomarker",
        "study",
        "treatment",
        "evidence",
        "oncology",
    }

    def route(self, query: str) -> str | None:
        """Return the most likely workflow id."""
        lowered = query.lower()
        scores = {workflow_id: 0 for workflow_id in self._RULES}

        for workflow_id, keywords in self._RULES.items():
            for keyword in keywords:
                if keyword in lowered:
                    scores[workflow_id] += 3 if " " in keyword else 2

        tokens = set(re.findall(r"[a-z0-9]+", lowered))
        if scores["evidence_brief"] == 0 and tokens & self._MEDICAL_TERMS:
            scores["evidence_brief"] = 1

        best_workflow, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score <= 0:
            return None
        return best_workflow
