"""Persistence for research reports and evidence artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from medclaw.evidence.models import Citation, ResearchReport


class EvidenceStore:
    """Persist research artifacts to the workspace."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.base_path = workspace / "research"
        self.reports_path = self.base_path / "reports"
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: ResearchReport) -> Path:
        """Save a structured research report to disk."""
        path = self._build_report_path(report)
        path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def save_report_artifacts(self, report: ResearchReport) -> dict[str, Path]:
        """Save the report plus structured companion artifacts."""
        report_path = self._build_report_path(report)
        report_slug = report_path.stem
        artifact_dir = self.reports_path / f"{report_slug}_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        report_payload = report.model_dump(mode="json")
        report_path.write_text(
            json.dumps(report_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        evidence_path = artifact_dir / "evidence.json"
        evidence_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in report.evidence],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        citations = self._collect_citations(report)
        citations_path = artifact_dir / "citations.json"
        citations_path.write_text(
            json.dumps(
                [citation.model_dump(mode="json") for citation in citations],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        metadata_path = artifact_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "workflow_id": report.workflow_id,
                    "question": report.question,
                    "title": report.title,
                    "generated_at": report.generated_at,
                    "artifact_dir": str(artifact_dir),
                    "report_path": str(report_path),
                    "evidence_count": len(report.evidence),
                    "citation_count": len(citations),
                    "metadata": report.metadata,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "report": report_path,
            "artifact_dir": artifact_dir,
            "evidence": evidence_path,
            "citations": citations_path,
            "metadata": metadata_path,
        }

    def list_reports(self) -> list[Path]:
        """List saved research reports, newest first."""
        return sorted(self.reports_path.glob("*.json"), reverse=True)

    def list_report_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """List report metadata records, newest first."""
        records = []
        for path in self.list_reports()[:limit]:
            try:
                report = self.load_report(path)
            except Exception:
                continue
            records.append(self._report_record(path, report))
        return records

    def search_report_records(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search saved reports by workflow id, title, question, and filename."""
        lowered = query.lower().strip()
        if not lowered:
            return self.list_report_records(limit=limit)

        results = []
        for record in self.list_report_records(limit=limit * 4):
            haystack = " ".join(
                [
                    record["filename"],
                    record["workflow_id"],
                    record["title"],
                    record["question"],
                ]
            ).lower()
            if lowered in haystack:
                results.append(record)
            if len(results) >= limit:
                break
        return results

    def load_report(self, path: Path | str) -> ResearchReport:
        """Load a structured research report from disk."""
        report_path = self.resolve_report_path(path)
        return ResearchReport.model_validate_json(report_path.read_text(encoding="utf-8"))

    def resolve_report_path(self, path: Path | str) -> Path:
        """Resolve a report path from an absolute path, relative path, or filename."""
        candidate = Path(path)
        if candidate.exists():
            return candidate
        report_path = self.reports_path / candidate.name
        if report_path.exists():
            return report_path
        raise FileNotFoundError(f"Could not find research report: {path}")

    def get_artifact_paths(self, path: Path | str) -> dict[str, Path]:
        """Return the file bundle associated with a saved report."""
        report_path = self.resolve_report_path(path)
        artifact_dir = self.reports_path / f"{report_path.stem}_artifacts"
        return {
            "report": report_path,
            "artifact_dir": artifact_dir,
            "evidence": artifact_dir / "evidence.json",
            "citations": artifact_dir / "citations.json",
            "metadata": artifact_dir / "metadata.json",
        }

    def read_artifact(self, path: Path | str, artifact: str = "report") -> Any:
        """Read a specific artifact payload."""
        artifact_paths = self.get_artifact_paths(path)
        if artifact not in artifact_paths:
            supported = ", ".join(sorted(artifact_paths))
            raise ValueError(f"Unsupported artifact '{artifact}'. Choose from: {supported}")
        target = artifact_paths[artifact]
        if artifact == "artifact_dir":
            return str(target)
        if artifact == "report":
            report = self.load_report(target)
            return report.model_dump(mode="json")
        return json.loads(target.read_text(encoding="utf-8"))

    def _build_report_path(self, report: ResearchReport) -> Path:
        """Build a timestamped report path."""
        slug = report.workflow_id.replace("/", "-").replace("_", "-")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{slug}.json"
        return self.reports_path / filename

    def _collect_citations(self, report: ResearchReport) -> list[Citation]:
        """Collect and deduplicate citations across evidence items."""
        citations: list[Citation] = []
        seen: set[tuple[str | None, str, str | None]] = set()
        for item in report.evidence:
            for citation in item.citations:
                key = (citation.identifier, citation.title, citation.url)
                if key in seen:
                    continue
                seen.add(key)
                citations.append(citation)
        return citations

    def _report_record(self, path: Path, report: ResearchReport) -> dict[str, Any]:
        """Build a compact index record for a saved report."""
        artifact_paths = self.get_artifact_paths(path)
        return {
            "path": str(path),
            "filename": path.name,
            "workflow_id": report.workflow_id,
            "title": report.title,
            "question": report.question,
            "generated_at": report.generated_at,
            "evidence_count": len(report.evidence),
            "artifact_dir": str(artifact_paths["artifact_dir"]),
        }
