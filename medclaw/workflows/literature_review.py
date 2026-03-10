"""Literature review workflow."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.gateways.medical import PubMedGateway
from medclaw.providers.base import LLMProvider
from medclaw.workflows.base import ResearchWorkflow


class LiteratureReviewWorkflow(ResearchWorkflow):
    """Review recent literature relevant to a biomedical question."""

    workflow_id = "literature_review"
    title = "Literature Review"

    def __init__(self, gateway: PubMedGateway | None = None):
        self.gateway = gateway or PubMedGateway()

    async def run(self, query: str, provider: LLMProvider | None) -> ResearchReport:
        evidence = await self.gateway.search(query, max_results=8)
        summary = await self.synthesize(
            query=query,
            provider=provider,
            evidence=evidence,
            instruction=(
                "Summarize the state of the evidence, note limits in retrieval, and mention "
                "that findings should be verified against full papers."
            ),
        )
        return ResearchReport(
            workflow_id=self.workflow_id,
            question=query,
            title=f"{self.title}: {query}",
            summary=summary,
            key_findings=[
                f"Retrieved {len(evidence)} literature records from PubMed.",
                "Use full texts and risk-of-bias review before making downstream decisions.",
            ],
            evidence=evidence,
        )
