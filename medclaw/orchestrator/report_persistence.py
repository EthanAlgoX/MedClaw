"""Persistence helpers for workflow reports and bundles."""

from __future__ import annotations

from pathlib import Path

from medclaw.evidence.models import ResearchReport
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
    ) -> ResearchReport:
        """Save a report and attach artifact metadata."""
        artifact_paths = self.evidence_store.save_report_artifacts(report)
        report.metadata["saved_path"] = str(artifact_paths["report"])
        report.metadata["artifact_dir"] = str(artifact_paths["artifact_dir"])
        report.metadata["artifact_paths"] = {
            name: str(path) for name, path in artifact_paths.items()
        }
        report.metadata["llm_enabled"] = llm_enabled
        return report

    def save_collection_bundle(self, reports: list[ResearchReport]) -> dict[str, Path]:
        """Persist a collection-level synthesis bundle across multiple workflow reports."""
        markdown_summary = render_collection_report_bundle(reports)
        return self.evidence_store.save_collection_bundle_artifacts(reports, markdown_summary)
