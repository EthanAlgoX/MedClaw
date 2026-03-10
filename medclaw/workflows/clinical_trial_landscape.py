"""Clinical trial landscape workflow."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.gateways.medical import ClinicalTrialsGateway
from medclaw.providers.base import LLMProvider
from medclaw.workflows.base import ResearchWorkflow


class ClinicalTrialLandscapeWorkflow(ResearchWorkflow):
    """Analyze recruiting and completed clinical trials for a topic."""

    workflow_id = "clinical_trial_landscape"
    title = "Clinical Trial Landscape"

    def __init__(self, gateway: ClinicalTrialsGateway | None = None):
        self.gateway = gateway or ClinicalTrialsGateway()

    async def run(self, query: str, provider: LLMProvider | None) -> ResearchReport:
        evidence = await self.gateway.search(query, max_results=8)
        summary = await self.synthesize(
            query=query,
            provider=provider,
            evidence=evidence,
            instruction=(
                "Summarize the trial landscape, highlight recruitment status where visible, "
                "and avoid making clinical recommendations."
            ),
        )
        return ResearchReport(
            workflow_id=self.workflow_id,
            question=query,
            title=f"{self.title}: {query}",
            summary=summary,
            key_findings=[
                f"Retrieved {len(evidence)} trial records from ClinicalTrials.gov.",
                "Eligibility, endpoints, and status should be verified on the source record.",
            ],
            evidence=evidence,
        )
