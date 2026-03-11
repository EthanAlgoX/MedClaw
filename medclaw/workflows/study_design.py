"""Study design workflow."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport
from medclaw.providers.base import LLMProvider
from medclaw.workflows.base import CollectionContext, ResearchWorkflow


class StudyDesignWorkflow(ResearchWorkflow):
    """Draft a study design memo for a research question."""

    workflow_id = "study_design"
    title = "Study Design Assistant"

    async def run(
        self,
        query: str,
        provider: LLMProvider | None,
        collection_context: CollectionContext | None = None,
    ) -> ResearchReport:
        summary = await self.synthesize(
            query=query,
            provider=provider,
            evidence=[],
            instruction=(
                "Draft a concise research design memo covering objective, study population, "
                "comparison groups, endpoints, confounders, and validation risks."
            ),
            collection_context=collection_context,
        )
        return ResearchReport(
            workflow_id=self.workflow_id,
            question=query,
            title=f"{self.title}: {query}",
            summary=summary,
            key_findings=[
                "No external evidence sources were retrieved for this design memo.",
                "Final protocol decisions should be reviewed by a domain expert and statistician.",
            ],
            evidence=[],
            metadata=self.build_report_metadata(collection_context),
        )
