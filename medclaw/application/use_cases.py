"""Top-level medical research use cases."""

from __future__ import annotations

from pathlib import Path

from medclaw.orchestrator.job_runner import ResearchOrchestrator
from medclaw.orchestrator.router import ResearchRouter
from medclaw.providers.base import LLMProvider


class MedicalResearchUseCases:
    """Application entrypoint for MedClaw research workflows."""

    def __init__(self, workspace: Path):
        self.router = ResearchRouter()
        self.orchestrator = ResearchOrchestrator(workspace)

    async def run_query(self, query: str, provider: LLMProvider) -> str | None:
        """Route a query to a typed research workflow when possible."""
        workflow_id = self.router.route(query)
        if workflow_id is None:
            return None

        report = await self.orchestrator.run(workflow_id, query, provider)
        return self.orchestrator.render(report)
