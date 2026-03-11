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

    async def run_query(self, query: str, provider: LLMProvider | None) -> str | None:
        """Route a query to a typed research workflow when possible."""
        workflow_id = self.router.route(query)
        if workflow_id is None:
            return None

        report = await self.orchestrator.run(workflow_id, query, provider)
        return self.orchestrator.render(report)

    async def run_collection(
        self,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
        workflow_id: str | None = None,
        all_preferred: bool = False,
    ) -> list[str]:
        """Run one or more workflows using collection preferences when available."""
        reports = await self.run_collection_reports(
            query=query,
            provider=provider,
            collection=collection,
            workflow_id=workflow_id,
            all_preferred=all_preferred,
        )
        return [self.orchestrator.render(report) for report in reports]

    async def run_workflow(
        self,
        workflow_id: str,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
    ) -> str:
        """Run a specific research workflow."""
        report = await self.orchestrator.run(workflow_id, query, provider, collection=collection)
        return self.orchestrator.render(report)

    async def run_workflow_report(
        self,
        workflow_id: str,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
    ):
        """Run a specific research workflow and return the structured report."""
        return await self.orchestrator.run(
            workflow_id,
            query,
            provider,
            collection=collection,
        )

    async def run_collection_reports(
        self,
        query: str,
        provider: LLMProvider | None,
        collection: str | None = None,
        workflow_id: str | None = None,
        all_preferred: bool = False,
        persist_bundle: bool = False,
    ) -> list:
        """Run collection-driven workflows and return structured reports."""
        workflow_ids = self._resolve_collection_run_workflows(
            query=query,
            collection=collection,
            workflow_id=workflow_id,
            all_preferred=all_preferred,
        )
        reports = []
        for selected_workflow in workflow_ids:
            reports.append(
                await self.orchestrator.run(
                    selected_workflow,
                    query,
                    provider,
                    collection=collection,
                )
            )
        if persist_bundle and len(reports) > 1:
            bundle_artifacts = self.orchestrator.save_collection_bundle(reports)
            bundle_paths = {name: str(path) for name, path in bundle_artifacts.items()}
            for report in reports:
                report.metadata["bundle_artifact_paths"] = bundle_paths
                report.metadata["bundle_saved_path"] = bundle_paths["bundle_markdown"]
        return reports

    def list_workflows(self) -> list[dict[str, str]]:
        """List available typed workflows."""
        return self.orchestrator.list_workflows()

    def _resolve_collection_run_workflows(
        self,
        query: str,
        collection: str | None,
        workflow_id: str | None,
        all_preferred: bool,
    ) -> list[str]:
        """Resolve which workflows to execute for a collection-aware run."""
        if workflow_id:
            return [workflow_id]

        preferred = self.orchestrator.resolve_collection_workflows(collection)
        if preferred:
            return preferred if all_preferred else [preferred[0]]

        routed = self.router.route(query)
        if routed is not None:
            return [routed]

        return ["evidence_brief"]
