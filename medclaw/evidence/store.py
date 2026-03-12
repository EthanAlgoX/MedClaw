"""Persistence for research reports and evidence artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from medclaw.evidence.artifacts import (
    REPORT_PATH_ARTIFACTS,
    BUNDLE_PATH_ARTIFACTS,
    build_unsupported_artifact_error,
    normalize_artifact_name,
)
from medclaw.evidence.api_models import (
    ArtifactRecord,
    CollectionManifest,
    CollectionRecord,
    artifact_record_from_dict,
    artifact_records_from_dicts,
    collection_manifest_from_dict,
    collection_record_from_dict,
    collection_records_from_dicts,
)
from medclaw.evidence.models import Citation, ResearchReport, ResearchRun


class EvidenceStore:
    """Persist research artifacts to the workspace."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.base_path = workspace / "research"
        self.reports_path = self.base_path / "reports"
        self.collections_path = self.base_path / "collections"
        self.runs_path = self.base_path / "runs"
        self.reports_path.mkdir(parents=True, exist_ok=True)
        self.collections_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(parents=True, exist_ok=True)

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

    def update_report_artifacts(
        self,
        report: ResearchReport,
        artifact_paths: dict[str, Path | str],
    ) -> None:
        """Rewrite report and metadata artifacts after post-save metadata changes."""
        report_path = Path(artifact_paths["report"])
        artifact_dir = Path(artifact_paths["artifact_dir"])
        metadata_path = Path(artifact_paths["metadata"])

        report_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        citations = self._collect_citations(report)
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

    def list_reports(self) -> list[Path]:
        """List saved research reports, newest first."""
        return sorted(self.reports_path.glob("*.json"), reverse=True)

    def save_run(self, run: ResearchRun) -> Path:
        """Save a structured research run to disk."""
        path = self._build_run_path(run)
        path.write_text(
            json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_run(self, path: Path | str) -> ResearchRun:
        """Load a structured research run from disk."""
        run_path = self.resolve_run_path(path)
        return ResearchRun.model_validate_json(run_path.read_text(encoding="utf-8"))

    def list_runs(self) -> list[Path]:
        """List saved research runs, newest first."""
        return sorted(self.runs_path.glob("*.json"), reverse=True)

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

    def list_artifact_records(
        self,
        query: str | None = None,
        kind: str | None = None,
        workflow_id: str | None = None,
        collection: str | None = None,
        since: str | None = None,
        until: str | None = None,
        latest: bool = False,
        latest_by_collection: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List saved report and bundle artifacts under a unified index."""
        if latest and latest_by_collection:
            raise ValueError("Choose either latest or latest_by_collection, not both")
        normalized_kind = self._normalize_artifact_kind(kind)
        include_reports = normalized_kind in {"all", "report"}
        include_bundles = normalized_kind in {"all", "collection_bundle"}

        report_records: list[dict[str, Any]] = []
        bundle_records: list[dict[str, Any]] = []
        if include_reports:
            report_records = self.filter_report_records(
                query=query,
                workflow_id=workflow_id,
                collection=collection,
                since=since,
                until=until,
                limit=limit * 2,
            )
        if include_bundles:
            bundle_records = self.filter_collection_bundle_records(
                query=query,
                workflow_id=workflow_id,
                collection=collection,
                since=since,
                until=until,
                limit=limit * 2,
        )
        records = report_records + bundle_records
        records.sort(key=lambda record: (record["generated_at"], record["kind"]), reverse=True)
        if latest:
            return records[:1]
        if latest_by_collection:
            return self._latest_records_by_collection(records, limit=limit)
        return records[:limit]

    def list_collection_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Aggregate saved reports by collection."""
        collections: dict[str, dict[str, Any]] = {}
        for manifest in self.list_collection_manifests(limit=1000):
            key = manifest["slug"]
            collections[key] = {
                "collection": manifest["name"],
                "slug": manifest["slug"],
                "objective": manifest["objective"],
                "disease_area": manifest["disease_area"],
                "owner": manifest["owner"],
                "tags": manifest["tags"],
                "preferred_workflows": manifest["preferred_workflows"],
                "created_at": manifest["created_at"],
                "updated_at": manifest["updated_at"],
                "report_count": 0,
                "evidence_count": 0,
                "citation_count": 0,
                "latest_generated_at": "",
                "latest_bundle_generated_at": "",
                "latest_bundle_markdown_path": "",
                "latest_bundle_json_path": "",
                "workflows": [],
                "titles": [],
            }

        for bundle_record in self.list_collection_bundle_records(limit=1000):
            key = bundle_record.get("collection_slug", "")
            if not key:
                continue
            entry = collections.get(key)
            if entry is None:
                collections[key] = {
                    "collection": bundle_record.get("collection", key),
                    "slug": key,
                    "objective": bundle_record.get("collection_objective", ""),
                    "disease_area": "",
                    "owner": "",
                    "tags": [],
                    "preferred_workflows": [],
                    "created_at": "",
                    "updated_at": "",
                    "report_count": 0,
                    "evidence_count": 0,
                    "citation_count": 0,
                    "latest_generated_at": "",
                    "latest_bundle_generated_at": bundle_record.get("generated_at", ""),
                    "latest_bundle_markdown_path": bundle_record.get("bundle_markdown_path", ""),
                    "latest_bundle_json_path": bundle_record.get("bundle_json_path", ""),
                    "workflows": [],
                    "titles": [],
                }
                continue

            if bundle_record.get("generated_at", "") > entry["latest_bundle_generated_at"]:
                entry["latest_bundle_generated_at"] = bundle_record.get("generated_at", "")
                entry["latest_bundle_markdown_path"] = bundle_record.get("bundle_markdown_path", "")
                entry["latest_bundle_json_path"] = bundle_record.get("bundle_json_path", "")

        for record in self.filter_report_records(limit=1000):
            collection = record["collection"]
            if not collection:
                continue
            key = self._slugify_collection_name(collection)
            entry = collections.get(key)
            if entry is None:
                collections[key] = {
                    "collection": collection,
                    "slug": key,
                    "objective": "",
                    "disease_area": "",
                    "owner": "",
                    "tags": [],
                    "preferred_workflows": [],
                    "created_at": "",
                    "updated_at": "",
                    "report_count": 1,
                    "evidence_count": record["evidence_count"],
                    "citation_count": record["citation_count"],
                    "latest_generated_at": record["generated_at"],
                    "latest_bundle_generated_at": "",
                    "latest_bundle_markdown_path": "",
                    "latest_bundle_json_path": "",
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
            key=lambda item: (
                item["latest_generated_at"]
                or item["latest_bundle_generated_at"]
                or item["updated_at"]
                or item["created_at"],
                item["collection"],
            ),
            reverse=True,
        )
        return ordered[:limit]

    def list_collection_record_models(self, limit: int = 50) -> list[CollectionRecord]:
        """Aggregate saved reports by collection as typed models."""
        return collection_records_from_dicts(self.list_collection_records(limit=limit))

    def get_collection_record_model(self, name_or_slug: str) -> CollectionRecord:
        """Resolve one collection aggregate record, synthesizing an empty record if needed."""
        manifest = self.load_collection_manifest_model(name_or_slug)
        for record in self.list_collection_record_models(limit=1000):
            if record.slug == manifest.slug:
                return record
        return collection_record_from_dict(
            {
                "collection": manifest.name,
                "slug": manifest.slug,
                "objective": manifest.objective,
                "disease_area": manifest.disease_area,
                "owner": manifest.owner,
                "tags": manifest.tags,
                "preferred_workflows": manifest.preferred_workflows,
                "created_at": manifest.created_at,
                "updated_at": manifest.updated_at,
                "report_count": 0,
                "evidence_count": 0,
                "citation_count": 0,
                "latest_generated_at": "",
                "latest_bundle_generated_at": "",
                "latest_bundle_markdown_path": "",
                "latest_bundle_json_path": "",
                "workflows": [],
                "titles": [],
            }
        )

    def save_collection_bundle_artifacts(
        self,
        reports: list[ResearchReport],
        markdown_summary: str,
    ) -> dict[str, Path]:
        """Save a collection-level synthesis bundle for multiple workflow reports."""
        if not reports:
            raise ValueError("Cannot save a collection bundle without reports")

        first_report = reports[0]
        collection = str(first_report.metadata.get("collection", "")).strip() or "research-bundle"
        collection_slug = self._slugify_collection_name(collection)
        bundle_slug = self._build_bundle_slug(collection_slug)
        artifact_dir = self.reports_path / f"{bundle_slug}_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = artifact_dir / "bundle_summary.md"
        markdown_path.write_text(markdown_summary, encoding="utf-8")

        bundle_payload = self._collection_bundle_payload(reports, markdown_path)
        bundle_json_path = artifact_dir / "bundle_summary.json"
        bundle_json_path.write_text(
            json.dumps(bundle_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        metadata_path = artifact_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "kind": "collection_bundle",
                    "collection": bundle_payload["collection"],
                    "collection_slug": bundle_payload["collection_slug"],
                    "generated_at": bundle_payload["generated_at"],
                    "artifact_dir": str(artifact_dir),
                    "bundle_markdown_path": str(markdown_path),
                    "bundle_json_path": str(bundle_json_path),
                    "report_count": bundle_payload["report_count"],
                    "evidence_count": bundle_payload["evidence_count"],
                    "citation_count": bundle_payload["citation_count"],
                    "workflow_ids": bundle_payload["workflow_ids"],
                    "report_titles": bundle_payload["report_titles"],
                    "collection_objective": bundle_payload["collection_objective"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "artifact_dir": artifact_dir,
            "bundle_markdown": markdown_path,
            "bundle_json": bundle_json_path,
            "metadata": metadata_path,
        }

    def list_collection_bundle_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """List saved collection synthesis bundles, newest first."""
        records = []
        for metadata_path in sorted(self.reports_path.glob("*_artifacts/metadata.json"), reverse=True):
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("kind") != "collection_bundle":
                continue
            records.append(payload)
            if len(records) >= limit:
                break
        return records

    def filter_collection_bundle_records(
        self,
        query: str | None = None,
        workflow_id: str | None = None,
        collection: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Filter saved collection bundle records."""
        lowered = query.lower().strip() if query else ""
        normalized_workflow = workflow_id.strip().lower() if workflow_id else ""
        normalized_collection = collection.strip().lower() if collection else ""
        since_date = self._parse_date_boundary(since, end_of_day=False) if since else None
        until_date = self._parse_date_boundary(until, end_of_day=True) if until else None

        records = []
        for payload in self.list_collection_bundle_records(limit=limit * 4):
            record = self._bundle_record(payload)
            if normalized_workflow and normalized_workflow != "collection_bundle":
                continue
            if normalized_collection and record["collection"].lower() != normalized_collection:
                continue
            if lowered:
                haystack = " ".join(
                    [
                        record["filename"],
                        record["collection"],
                        record["title"],
                        record["summary_preview"],
                        " ".join(record["workflow_ids"]),
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

    def save_collection_manifest(
        self,
        name: str,
        objective: str = "",
        disease_area: str = "",
        owner: str = "",
        tags: list[str] | None = None,
        preferred_workflows: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create or update a collection manifest."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Collection name cannot be empty")

        slug = self._slugify_collection_name(normalized_name)
        path = self.collections_path / f"{slug}.json"
        now = datetime.now(timezone.utc).isoformat()
        existing: dict[str, Any] = {}
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))

        payload = {
            "name": normalized_name,
            "slug": slug,
            "objective": objective.strip(),
            "disease_area": disease_area.strip(),
            "owner": owner.strip(),
            "tags": self._normalize_string_list(tags or []),
            "preferred_workflows": self._normalize_string_list(preferred_workflows or []),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload

    def load_collection_manifest(self, name_or_slug: str) -> dict[str, Any]:
        """Load a collection manifest by display name or slug."""
        normalized = name_or_slug.strip()
        if not normalized:
            raise FileNotFoundError("Collection name cannot be empty")

        direct_path = self.collections_path / f"{self._slugify_collection_name(normalized)}.json"
        if direct_path.exists():
            return json.loads(direct_path.read_text(encoding="utf-8"))

        for manifest in self.list_collection_manifests(limit=1000):
            if manifest["name"].lower() == normalized.lower():
                return manifest

        raise FileNotFoundError(f"Could not find research collection: {name_or_slug}")

    def load_collection_manifest_model(self, name_or_slug: str) -> CollectionManifest:
        """Load a collection manifest as a typed model."""
        return collection_manifest_from_dict(self.load_collection_manifest(name_or_slug))

    def list_collection_manifests(self, limit: int = 50) -> list[dict[str, Any]]:
        """List saved collection manifests, newest first."""
        manifests = []
        for path in sorted(self.collections_path.glob("*.json"), reverse=True):
            try:
                manifests.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            if len(manifests) >= limit:
                break
        return manifests

    def load_report(self, path: Path | str) -> ResearchReport:
        """Load a structured research report from disk."""
        report_path = self.resolve_report_path(path)
        return ResearchReport.model_validate_json(report_path.read_text(encoding="utf-8"))

    def resolve_report_path(self, path: Path | str) -> Path:
        """Resolve a report path from an absolute path, relative path, or filename."""
        candidate = Path(path)
        if candidate.exists() and candidate.is_file():
            return candidate
        report_path = self.reports_path / candidate.name
        if report_path.exists() and report_path.is_file():
            return report_path
        raise FileNotFoundError(f"Could not find research report: {path}")

    def resolve_run_path(self, path: Path | str) -> Path:
        """Resolve a run path from an absolute path, relative path, or filename."""
        candidate = Path(path)
        if candidate.exists() and candidate.is_file():
            return candidate
        run_path = self.runs_path / candidate.name
        if run_path.exists() and run_path.is_file():
            return run_path
        if candidate.suffix != ".json":
            suffixed_path = self.runs_path / f"{candidate.name}.json"
            if suffixed_path.exists() and suffixed_path.is_file():
                return suffixed_path
        raise FileNotFoundError(f"Could not find research run: {path}")

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

    def get_bundle_artifact_paths(self, path: Path | str) -> dict[str, Path]:
        """Return the file bundle associated with a saved collection summary."""
        artifact_dir = self.resolve_bundle_artifact_dir(path)
        return {
            "artifact_dir": artifact_dir,
            "bundle_markdown": artifact_dir / "bundle_summary.md",
            "bundle_json": artifact_dir / "bundle_summary.json",
            "metadata": artifact_dir / "metadata.json",
        }

    def read_artifact(self, path: Path | str, artifact: str = "report") -> Any:
        """Read a specific artifact payload."""
        normalized_artifact = normalize_artifact_name(
            artifact,
            choices=REPORT_PATH_ARTIFACTS + ("bundle_markdown", "bundle_json"),
        )
        assert normalized_artifact is not None
        if normalized_artifact in {"bundle_markdown", "bundle_json"}:
            return self.read_bundle_artifact(path, artifact=normalized_artifact)
        artifact_paths = self.get_artifact_paths(path)
        if normalized_artifact not in artifact_paths:
            raise build_unsupported_artifact_error(artifact, REPORT_PATH_ARTIFACTS)
        target = artifact_paths[normalized_artifact]
        if normalized_artifact == "artifact_dir":
            return str(target)
        if normalized_artifact == "report":
            report = self.load_report(target)
            return report.model_dump(mode="json")
        return json.loads(target.read_text(encoding="utf-8"))

    def read_bundle_artifact(self, path: Path | str, artifact: str = "bundle_markdown") -> Any:
        """Read a saved collection bundle artifact."""
        normalized_artifact = normalize_artifact_name(
            artifact,
            choices=BUNDLE_PATH_ARTIFACTS,
            kind="collection_bundle",
        )
        assert normalized_artifact is not None
        artifact_paths = self.get_bundle_artifact_paths(path)
        if normalized_artifact not in artifact_paths:
            raise build_unsupported_artifact_error(artifact, BUNDLE_PATH_ARTIFACTS, kind="collection_bundle")
        target = artifact_paths[normalized_artifact]
        if normalized_artifact == "artifact_dir":
            return str(target)
        if normalized_artifact == "bundle_markdown":
            return target.read_text(encoding="utf-8")
        return json.loads(target.read_text(encoding="utf-8"))

    def get_artifact_record(self, path: Path | str) -> dict[str, Any]:
        """Resolve a saved report or bundle into its unified index record."""
        try:
            report_path = self.resolve_report_path(path)
            return self._report_record(report_path, self.load_report(report_path))
        except FileNotFoundError as report_error:
            try:
                payload = self.read_bundle_artifact(path, artifact="metadata")
                return self._bundle_record(payload)
            except (FileNotFoundError, ValueError):
                raise report_error

    def get_artifact_record_model(self, path: Path | str) -> ArtifactRecord:
        """Resolve a saved report or bundle into a typed artifact record."""
        return artifact_record_from_dict(self.get_artifact_record(path))

    def list_artifact_record_models(
        self,
        query: str | None = None,
        kind: str | None = None,
        workflow_id: str | None = None,
        collection: str | None = None,
        since: str | None = None,
        until: str | None = None,
        latest: bool = False,
        latest_by_collection: bool = False,
        limit: int = 50,
    ) -> list[ArtifactRecord]:
        """List saved report and bundle artifacts as typed models."""
        return artifact_records_from_dicts(
            self.list_artifact_records(
                query=query,
                kind=kind,
                workflow_id=workflow_id,
                collection=collection,
                since=since,
                until=until,
                latest=latest,
                latest_by_collection=latest_by_collection,
                limit=limit,
            )
        )

    def _build_report_path(self, report: ResearchReport) -> Path:
        """Build a timestamped report path."""
        slug = report.workflow_id.replace("/", "-").replace("_", "-")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{slug}.json"
        return self.reports_path / filename

    def _build_run_path(self, run: ResearchRun) -> Path:
        """Build a timestamped run path."""
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{run.id}.json"
        return self.runs_path / filename

    def _build_bundle_slug(self, collection_slug: str) -> str:
        """Build a timestamped collection bundle slug."""
        return f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{collection_slug}_collection-bundle"

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
            "kind": "report",
            "id": path.name,
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

    def _bundle_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build a compact index record for a saved collection bundle."""
        artifact_dir = Path(payload["artifact_dir"])
        collection = payload.get("collection", "")
        workflow_ids = payload.get("workflow_ids", [])
        report_titles = payload.get("report_titles", [])
        return {
            "kind": "collection_bundle",
            "id": artifact_dir.name,
            "path": str(artifact_dir),
            "filename": artifact_dir.name,
            "collection": collection,
            "workflow_id": "collection_bundle",
            "title": f"Collection Brief: {collection}",
            "question": "",
            "generated_at": payload.get("generated_at", ""),
            "evidence_count": payload.get("evidence_count", 0),
            "citation_count": payload.get("citation_count", 0),
            "summary_preview": self._summary_preview(
                payload.get("collection_objective", "")
                or ", ".join(report_titles[:2])
            ),
            "artifact_dir": str(artifact_dir),
            "bundle_markdown_path": payload.get("bundle_markdown_path", ""),
            "bundle_json_path": payload.get("bundle_json_path", ""),
            "report_count": payload.get("report_count", 0),
            "workflow_ids": workflow_ids,
        }

    def _collection_bundle_payload(
        self,
        reports: list[ResearchReport],
        markdown_path: Path,
    ) -> dict[str, Any]:
        """Build a JSON payload for a collection synthesis bundle."""
        first_report = reports[0]
        collection = str(first_report.metadata.get("collection", "")).strip() or "research-bundle"
        collection_slug = self._slugify_collection_name(collection)
        generated_at = datetime.now(timezone.utc).isoformat()
        workflow_ids = [report.workflow_id for report in reports]
        report_paths = [
            str(report.metadata["saved_path"])
            for report in reports
            if report.metadata.get("saved_path")
        ]
        evidence_count = sum(len(report.evidence) for report in reports)
        citation_count = sum(
            len(self._collect_citations(report))
            for report in reports
        )
        return {
            "kind": "collection_bundle",
            "collection": collection,
            "collection_slug": collection_slug,
            "collection_objective": first_report.metadata.get("collection_objective", ""),
            "generated_at": generated_at,
            "report_count": len(reports),
            "workflow_ids": workflow_ids,
            "report_titles": [report.title for report in reports],
            "report_paths": report_paths,
            "evidence_count": evidence_count,
            "citation_count": citation_count,
            "bundle_markdown_path": str(markdown_path),
        }

    def _summary_preview(self, summary: str, max_length: int = 160) -> str:
        """Return a compact single-line summary preview."""
        compact = " ".join(summary.split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 1].rstrip() + "…"

    def _normalize_string_list(self, values: list[str]) -> list[str]:
        """Normalize repeated string values while preserving order."""
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = value.strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _slugify_collection_name(self, name: str) -> str:
        """Create a filesystem-safe collection slug."""
        slug_chars = [
            char.lower() if char.isalnum() else "-"
            for char in name.strip()
        ]
        slug = "".join(slug_chars)
        while "--" in slug:
            slug = slug.replace("--", "-")
        slug = slug.strip("-")
        if not slug:
            raise ValueError("Collection name must include letters or numbers")
        return slug

    def _normalize_artifact_kind(self, kind: str | None) -> str:
        """Normalize artifact kind filter values."""
        if kind is None:
            return "all"
        normalized = kind.strip().lower().replace("-", "_")
        aliases = {
            "all": "all",
            "report": "report",
            "reports": "report",
            "bundle": "collection_bundle",
            "bundles": "collection_bundle",
            "collection_bundle": "collection_bundle",
        }
        if normalized not in aliases:
            supported = ", ".join(sorted(aliases))
            raise ValueError(f"Unsupported artifact kind '{kind}'. Choose from: {supported}")
        return aliases[normalized]

    def _latest_records_by_collection(
        self,
        records: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Keep only the newest artifact for each named collection."""
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in records:
            collection = record.get("collection", "").strip()
            if not collection:
                continue
            key = collection.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(record)
            if len(deduped) >= limit:
                break
        return deduped

    def resolve_bundle_artifact_dir(self, path: Path | str) -> Path:
        """Resolve a collection bundle artifact directory from an id, dir, or file path."""
        candidate = Path(path)
        if candidate.exists():
            if candidate.is_dir():
                return candidate
            if candidate.parent.is_dir():
                return candidate.parent

        direct_dir = self.reports_path / candidate.name
        if direct_dir.is_dir():
            return direct_dir

        if not candidate.name.endswith("_artifacts"):
            suffixed_dir = self.reports_path / f"{candidate.name}_artifacts"
            if suffixed_dir.is_dir():
                return suffixed_dir

        raise FileNotFoundError(f"Could not find collection bundle artifact: {path}")

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
