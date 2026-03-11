"""Drug and target landscape workflow."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.gateways.medical import DrugGateway, PubMedGateway
from medclaw.providers.base import LLMProvider
from medclaw.workflows.base import CollectionContext, ResearchWorkflow


class DrugTargetLandscapeWorkflow(ResearchWorkflow):
    """Summarize drug or target-oriented evidence for a query."""

    workflow_id = "drug_target_landscape"
    title = "Drug / Target Landscape"

    def __init__(
        self,
        drug_gateway: DrugGateway | None = None,
        literature_gateway: PubMedGateway | None = None,
    ):
        self.drug_gateway = drug_gateway or DrugGateway()
        self.literature_gateway = literature_gateway or PubMedGateway()

    async def run(
        self,
        query: str,
        provider: LLMProvider | None,
        collection_context: CollectionContext | None = None,
    ) -> ResearchReport:
        drug_items = await self.drug_gateway.search(query)
        literature_items = await self.literature_gateway.search(query, max_results=4)
        evidence = drug_items + literature_items
        summary = await self.synthesize(
            query=query,
            provider=provider,
            evidence=evidence,
            instruction=(
                "Summarize the available drug/target context and clearly separate placeholder "
                "drug records from literature-backed findings."
            ),
            collection_context=collection_context,
        )
        return ResearchReport(
            workflow_id=self.workflow_id,
            question=query,
            title=f"{self.title}: {query}",
            summary=summary,
            key_findings=[
                f"Collected {len(drug_items)} drug records and {len(literature_items)} literature records.",
                "Drug lookup support is currently limited and should be expanded with richer sources.",
            ],
            evidence=evidence,
            metadata=self.build_report_metadata(collection_context),
        )
