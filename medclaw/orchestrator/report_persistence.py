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
        report.metadata["workflow_run_id"] = run.id
        report.metadata["workflow_run_path"] = str(run_path)
        report.metadata["run_id"] = run.id
        report.metadata["run_path"] = str(run_path)
        report.metadata["run_scope"] = "workflow"
        self.evidence_store.update_report_artifacts(report, artifact_paths)
        return report

    def save_collection_bundle(self, reports: list[ResearchReport]) -> dict[str, Path]:
        """Persist a collection-level synthesis bundle across multiple workflow reports."""
        markdown_summary = render_collection_report_bundle(reports)
        return self.evidence_store.save_collection_bundle_artifacts(reports, markdown_summary)

    def persist_collection_run(
        self,
        reports: list[ResearchReport],
        *,
        query: str,
        collection: str | None = None,
        bundle_artifacts: dict[str, Path] | None = None,
    ) -> ResearchRun:
        """Persist one aggregate research run spanning multiple workflow reports."""
        if not reports:
            raise ValueError("Cannot persist a collection run without reports")

        normalized_collection = (collection or "").strip() or str(
            reports[0].metadata.get("collection", "")
        ).strip()
        bundle_paths = (
            {name: str(path) for name, path in bundle_artifacts.items()}
            if bundle_artifacts
            else {}
        )
        workflow_runs = [self._workflow_run_from_report(report) for report in reports]
        timestamps = [report.generated_at for report in reports if report.generated_at]
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc).isoformat()
        completed_at = max(timestamps) if timestamps else started_at
        run = ResearchRun(
            query=query,
            collection=normalized_collection,
            started_at=started_at,
            completed_at=completed_at,
            workflow_runs=workflow_runs,
            metadata={
                "workflow_count": len(workflow_runs),
                "persisted_at": datetime.now(timezone.utc).isoformat(),
                "report_paths": [
                    workflow_run.report_path
                    for workflow_run in workflow_runs
                    if workflow_run.report_path
                ],
                "bundle_artifact_paths": bundle_paths,
                "bundle_saved_path": bundle_paths.get("bundle_markdown", ""),
            },
        )
        run_path = self.evidence_store.save_run(run)
        for report in reports:
            report.metadata.setdefault("workflow_run_id", report.metadata.get("run_id", ""))
            report.metadata.setdefault("workflow_run_path", report.metadata.get("run_path", ""))
            report.metadata["run_id"] = run.id
            report.metadata["run_path"] = str(run_path)
            report.metadata["run_scope"] = "collection"
            if bundle_paths:
                report.metadata["bundle_artifact_paths"] = bundle_paths
                report.metadata["bundle_saved_path"] = bundle_paths["bundle_markdown"]
            if self._can_update_report_artifacts(report):
                self.evidence_store.update_report_artifacts(
                    report,
                    report.metadata["artifact_paths"],
                )
        return run

    def _workflow_run_from_report(self, report: ResearchReport) -> WorkflowRun:
        """Project one persisted report into a workflow run record."""
        artifact_paths = report.metadata.get("artifact_paths", {})
        if not isinstance(artifact_paths, dict):
            artifact_paths = {}
        payload = {
            "workflow_id": report.workflow_id,
            "question": report.question,
            "llm_enabled": bool(report.metadata.get("llm_enabled", False)),
            "provider_name": str(report.metadata.get("provider_name", "")).strip(),
            "model_name": str(report.metadata.get("model_name", "")).strip(),
            "started_at": report.generated_at,
            "completed_at": report.generated_at,
            "report_path": str(report.metadata.get("saved_path", "")).strip(),
            "artifact_dir": str(report.metadata.get("artifact_dir", "")).strip(),
            "artifact_paths": {str(name): str(path) for name, path in artifact_paths.items()},
            "metadata": {
                "collection": str(report.metadata.get("collection", "")).strip(),
                "collection_slug": str(report.metadata.get("collection_slug", "")).strip(),
            },
        }
        workflow_run_id = str(report.metadata.get("workflow_run_id") or report.metadata.get("run_id") or "").strip()
        if workflow_run_id:
            payload["id"] = workflow_run_id
        return WorkflowRun(**payload)

    def _can_update_report_artifacts(self, report: ResearchReport) -> bool:
        """Check whether a report has persisted artifacts that can be rewritten."""
        artifact_paths = report.metadata.get("artifact_paths")
        if not isinstance(artifact_paths, dict):
            return False
        required = {"report", "artifact_dir", "metadata"}
        if not required.issubset(artifact_paths):
            return False
        return all(Path(artifact_paths[name]).exists() for name in required)
