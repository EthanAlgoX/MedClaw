"""Persistence helpers for workflow reports and bundles."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from medclaw.evidence.models import ResearchReport, ResearchRun, WorkflowRun
from medclaw.evidence.store import EvidenceStore
from medclaw.reporting.briefs import render_collection_report_bundle


class ReportPersistenceService:
    """Persist workflow reports and collection bundle artifacts."""

    def __init__(self, evidence_store: EvidenceStore):
        self.evidence_store = evidence_store

    def persist_report(
        self,
        report: ResearchReport,
        *,
        llm_enabled: bool,
        provider_name: str = "",
        model_name: str = "",
    ) -> ResearchReport:
        """Save a report and attach artifact metadata."""
        report.metadata["llm_enabled"] = llm_enabled
        if provider_name:
            report.metadata["provider_name"] = provider_name
        if model_name:
            report.metadata["model_name"] = model_name

        artifact_paths = self.evidence_store.save_report_artifacts(report)
        report.metadata["saved_path"] = str(artifact_paths["report"])
        report.metadata["artifact_dir"] = str(artifact_paths["artifact_dir"])
        report.metadata["artifact_paths"] = {
            name: str(path) for name, path in artifact_paths.items()
        }
        workflow_run = WorkflowRun(
            workflow_id=report.workflow_id,
            question=report.question,
            llm_enabled=llm_enabled,
            provider_name=provider_name,
            model_name=model_name,
            started_at=report.generated_at,
            completed_at=report.generated_at,
            report_path=report.metadata["saved_path"],
            artifact_dir=report.metadata["artifact_dir"],
            artifact_paths=report.metadata["artifact_paths"],
            metadata={
                "collection": str(report.metadata.get("collection", "")).strip(),
                "collection_slug": str(report.metadata.get("collection_slug", "")).strip(),
            },
        )
        run = ResearchRun(
            query=report.question,
            collection=str(report.metadata.get("collection", "")).strip(),
            started_at=report.generated_at,
            completed_at=report.generated_at,
            workflow_runs=[workflow_run],
            metadata={
                "workflow_count": 1,
                "persisted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        run_path = self.evidence_store.save_run(run)
        report.metadata["run_id"] = run.id
        report.metadata["run_path"] = str(run_path)
        self.evidence_store.update_report_artifacts(report, artifact_paths)
        return report

    def save_collection_bundle(self, reports: list[ResearchReport]) -> dict[str, Path]:
        """Persist a collection-level synthesis bundle across multiple workflow reports."""
        markdown_summary = render_collection_report_bundle(reports)
        return self.evidence_store.save_collection_bundle_artifacts(reports, markdown_summary)
