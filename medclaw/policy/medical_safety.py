"""Safety checks for medical research outputs."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport


class MedicalSafetyPolicy:
    """Apply basic policy rules to MedClaw research reports."""

    def build_disclaimer(self, workflow_id: str) -> str:
        """Return a workflow-appropriate disclaimer."""
        if workflow_id == "study_design":
            return (
                "This output supports research planning only and is not a substitute for "
                "biostatistical review, ethics review, or clinical decision-making."
            )
        return (
            "This output is a research aid. Verify primary sources, assess study quality, "
            "and do not treat it as direct medical advice."
        )

    def apply(self, report: ResearchReport) -> ResearchReport:
        """Attach policy metadata and disclaimers."""
        report.disclaimer = self.build_disclaimer(report.workflow_id)
        report.metadata.setdefault("policy", {})
        report.metadata["policy"]["citation_count"] = sum(
            len(item.citations) for item in report.evidence
        )
        report.metadata["policy"]["evidence_count"] = len(report.evidence)
        report.metadata["policy"]["research_only"] = True
        return report
