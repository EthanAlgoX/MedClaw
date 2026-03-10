"""Evidence brief workflow."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.gateways.medical import ClinicalTrialsGateway, PubMedGateway
from medclaw.providers.base import LLMProvider
from medclaw.workflows.base import ResearchWorkflow


class EvidenceBriefWorkflow(ResearchWorkflow):
    """Create a concise evidence brief from literature and trial sources."""

    workflow_id = "evidence_brief"
    title = "Evidence Brief"

    def __init__(
        self,
        literature_gateway: PubMedGateway | None = None,
        trials_gateway: ClinicalTrialsGateway | None = None,
    ):
        self.literature_gateway = literature_gateway or PubMedGateway()
        self.trials_gateway = trials_gateway or ClinicalTrialsGateway()

    async def run(self, query: str, provider: LLMProvider | None) -> ResearchReport:
        literature = await self.literature_gateway.search(query, max_results=5)
        trials = await self.trials_gateway.search(query, max_results=3)
        evidence = literature + trials
        summary = await self.synthesize(
            query=query,
            provider=provider,
            evidence=evidence,
            instruction=(
                "Create a short evidence brief that combines literature and trial signals, "
                "and call out any missing or weak evidence."
            ),
        )
        return ResearchReport(
            workflow_id=self.workflow_id,
            question=query,
            title=f"{self.title}: {query}",
            summary=summary,
            key_findings=[
                f"Retrieved {len(literature)} literature records and {len(trials)} trial records.",
                "This brief is intended for rapid orientation, not final evidence grading.",
            ],
            evidence=evidence,
        )
