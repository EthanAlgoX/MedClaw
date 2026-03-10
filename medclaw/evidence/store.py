"""Persistence for research reports and evidence artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
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
        return self.filter_report_records(limit=limit)

    def search_report_records(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search saved reports by workflow id, title, question, and filename."""
        return self.filter_report_records(query=query, limit=limit)

    def filter_report_records(
        self,
        query: str | None = None,
        workflow_id: str | None = None,
        collection: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Filter saved report records by query, workflow, and generated date."""
        lowered = query.lower().strip() if query else ""
        normalized_workflow = workflow_id.strip().lower() if workflow_id else ""
        normalized_collection = collection.strip().lower() if collection else ""
        since_date = self._parse_date_boundary(since, end_of_day=False) if since else None
        until_date = self._parse_date_boundary(until, end_of_day=True) if until else None

        records = []
        for path in self.list_reports():
            try:
                report = self.load_report(path)
            except Exception:
                continue

            record = self._report_record(path, report)
            if normalized_workflow and record["workflow_id"].lower() != normalized_workflow:
                continue
            if normalized_collection and record["collection"].lower() != normalized_collection:
                continue
            if lowered:
                haystack = " ".join(
                    [
                        record["filename"],
                        record["collection"],
                        record["workflow_id"],
                        record["title"],
                        record["question"],
                        record["summary_preview"],
                    ]
                ).lower()
                if lowered not in haystack:
                    continue
            generated_at = self._parse_generated_at(record["generated_at"])
            if since_date and generated_at < since_date:
                continue
            if until_date and generated_at > until_date:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        return records

    def list_collection_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Aggregate saved reports by collection."""
        collections: dict[str, dict[str, Any]] = {}
        for record in self.filter_report_records(limit=1000):
            collection = record["collection"]
            if not collection:
                continue
            entry = collections.get(collection)
            if entry is None:
                collections[collection] = {
                    "collection": collection,
                    "report_count": 1,
                    "evidence_count": record["evidence_count"],
                    "citation_count": record["citation_count"],
                    "latest_generated_at": record["generated_at"],
                    "workflows": [record["workflow_id"]],
                    "titles": [record["title"]],
                }
                continue

            entry["report_count"] += 1
            entry["evidence_count"] += record["evidence_count"]
            entry["citation_count"] += record["citation_count"]
            if record["generated_at"] > entry["latest_generated_at"]:
                entry["latest_generated_at"] = record["generated_at"]
            if record["workflow_id"] not in entry["workflows"]:
                entry["workflows"].append(record["workflow_id"])
            entry["titles"].append(record["title"])

        ordered = sorted(
            collections.values(),
            key=lambda item: (item["latest_generated_at"], item["collection"]),
            reverse=True,
        )
        return ordered[:limit]

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
            "collection": str(report.metadata.get("collection", "")).strip(),
            "workflow_id": report.workflow_id,
            "title": report.title,
            "question": report.question,
            "generated_at": report.generated_at,
            "evidence_count": len(report.evidence),
            "citation_count": len(self._collect_citations(report)),
            "summary_preview": self._summary_preview(report.summary),
            "artifact_dir": str(artifact_paths["artifact_dir"]),
        }

    def _summary_preview(self, summary: str, max_length: int = 160) -> str:
        """Return a compact single-line summary preview."""
        compact = " ".join(summary.split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 1].rstrip() + "…"

    def _parse_generated_at(self, value: str) -> datetime:
        """Parse a stored report timestamp."""
        generated_at = datetime.fromisoformat(value)
        if generated_at.tzinfo is None:
            return generated_at.replace(tzinfo=timezone.utc)
        return generated_at

    def _parse_date_boundary(self, value: str, end_of_day: bool) -> datetime:
        """Parse a YYYY-MM-DD boundary into a timezone-aware datetime."""
        parsed_date = date.fromisoformat(value)
        boundary_time = time.max if end_of_day else time.min
        return datetime.combine(parsed_date, boundary_time, tzinfo=timezone.utc)
