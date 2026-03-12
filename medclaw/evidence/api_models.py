"""Typed response models for research artifact APIs."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport, ResearchRun


class ResearchReportResponse(BaseModel):
    """Typed single-report response."""

    report: ResearchReport


class ResearchReportListResponse(BaseModel):
    """Typed multi-report response."""

    items: list[ResearchReport]
    total: int


class ResearchRunRecord(BaseModel):
    """Saved research run index record."""

    id: str
    path: str
    filename: str
    scope: Literal["workflow", "collection"]
    query: str
    collection: str = ""
    status: str = "completed"
    started_at: str
    completed_at: str
    workflow_count: int = 0
    workflow_ids: list[str] = Field(default_factory=list)
    bundle_saved_path: str = ""


class ResearchRunQueryFilters(BaseModel):
    """Query filters applied to research run listing endpoints."""

    query: str | None = None
    collection: str | None = None
    workflow_id: str | None = None
    latest: bool = False
    limit: int = 50


class ResearchRunListResponse(BaseModel):
    """Typed research run list response."""

    items: list[ResearchRunRecord]
    total: int
    filters: ResearchRunQueryFilters


class ResearchRunResponse(BaseModel):
    """Typed resolved research run response."""

    target: str
    path: str
    record: ResearchRunRecord
    run: ResearchRun


class ResearchTimelineRecord(BaseModel):
    """One event in the unified research project timeline."""

    kind: Literal["report", "collection_bundle", "research_run"]
    id: str
    path: str
    collection: str = ""
    timestamp: str
    title: str
    query: str = ""
    workflow_ids: list[str] = Field(default_factory=list)
    scope: str = ""
    summary_preview: str = ""


class ResearchTimelineQueryFilters(BaseModel):
    """Query filters applied to research timeline endpoints."""

    query: str | None = None
    collection: str | None = None
    workflow_id: str | None = None
    limit: int = 50


class ResearchTimelineListResponse(BaseModel):
    """Typed research timeline response."""

    items: list[ResearchTimelineRecord]
    total: int
    filters: ResearchTimelineQueryFilters


class ReportArtifactRecord(BaseModel):
    """Saved report artifact index record."""

    kind: Literal["report"]
    id: str
    path: str
    filename: str
    collection: str = ""
    workflow_id: str
    title: str
    question: str
    generated_at: str
    evidence_count: int = 0
    citation_count: int = 0
    summary_preview: str = ""
    artifact_dir: str


class CollectionBundleArtifactRecord(BaseModel):
    """Saved collection bundle artifact index record."""

    kind: Literal["collection_bundle"]
    id: str
    path: str
    filename: str
    collection: str = ""
    workflow_id: Literal["collection_bundle"] = "collection_bundle"
    title: str
    question: str = ""
    generated_at: str
    evidence_count: int = 0
    citation_count: int = 0
    summary_preview: str = ""
    artifact_dir: str
    bundle_markdown_path: str = ""
    bundle_json_path: str = ""
    report_count: int = 0
    workflow_ids: list[str] = Field(default_factory=list)


ArtifactRecord = Annotated[
    ReportArtifactRecord | CollectionBundleArtifactRecord,
    Field(discriminator="kind"),
]

ArtifactPayload = ResearchReport | list[EvidenceItem] | list[Citation] | dict[str, Any] | str

_ARTIFACT_RECORD_ADAPTER = TypeAdapter(ArtifactRecord)
_ARTIFACT_RECORD_LIST_ADAPTER = TypeAdapter(list[ArtifactRecord])
_RUN_RECORD_ADAPTER = TypeAdapter(ResearchRunRecord)
_RUN_RECORD_LIST_ADAPTER = TypeAdapter(list[ResearchRunRecord])
_TIMELINE_RECORD_ADAPTER = TypeAdapter(ResearchTimelineRecord)
_TIMELINE_RECORD_LIST_ADAPTER = TypeAdapter(list[ResearchTimelineRecord])


class ArtifactQueryFilters(BaseModel):
    """Query filters applied to artifact listing endpoints."""

    query: str | None = None
    kind: str | None = None
    workflow_id: str | None = None
    collection: str | None = None
    since: str | None = None
    until: str | None = None
    latest: bool = False
    latest_by_collection: bool = False
    limit: int = 50


class ArtifactListResponse(BaseModel):
    """Typed artifact index response."""

    items: list[ArtifactRecord]
    total: int
    filters: ArtifactQueryFilters


class ArtifactPayloadResponse(BaseModel):
    """Typed resolved artifact payload response."""

    target: str
    artifact: str
    kind: str
    path: str
    format: Literal["json", "markdown"]
    record: ArtifactRecord | None = None
    payload: ArtifactPayload


class ArtifactPayloadListResponse(BaseModel):
    """Typed resolved artifact payload list response."""

    items: list[ArtifactPayloadResponse]
    total: int
    filters: ArtifactQueryFilters | None = None


class CollectionManifest(BaseModel):
    """Saved collection manifest payload."""

    name: str
    slug: str
    objective: str = ""
    disease_area: str = ""
    owner: str = ""
    tags: list[str] = Field(default_factory=list)
    preferred_workflows: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class CollectionRecord(BaseModel):
    """Collection registry record with aggregate stats."""

    collection: str
    slug: str
    objective: str = ""
    disease_area: str = ""
    owner: str = ""
    tags: list[str] = Field(default_factory=list)
    preferred_workflows: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    report_count: int = 0
    evidence_count: int = 0
    citation_count: int = 0
    latest_generated_at: str = ""
    latest_bundle_generated_at: str = ""
    latest_bundle_markdown_path: str = ""
    latest_bundle_json_path: str = ""
    latest_run_id: str = ""
    latest_run_completed_at: str = ""
    latest_activity_at: str = ""
    stale: bool = False
    stale_days: int | None = None
    health_signals: list[str] = Field(default_factory=list)
    missing_preferred_workflows: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)


class CollectionResponse(BaseModel):
    """Typed single-collection response."""

    item: CollectionRecord | CollectionManifest


class CollectionListResponse(BaseModel):
    """Typed collection list response."""

    items: list[CollectionRecord]
    total: int
    limit: int


class CollectionDashboard(BaseModel):
    """Unified collection dashboard across registry, artifacts, runs, and timeline."""

    collection: CollectionRecord
    latest_report: ArtifactRecord | None = None
    latest_bundle: ArtifactRecord | None = None
    latest_run: ResearchRunRecord | None = None
    timeline: list[ResearchTimelineRecord] = Field(default_factory=list)
    covered_workflows: list[str] = Field(default_factory=list)
    missing_preferred_workflows: list[str] = Field(default_factory=list)
    latest_activity_at: str = ""
    stale: bool = False
    stale_days: int | None = None
    health_signals: list[str] = Field(default_factory=list)


class CollectionDashboardResponse(BaseModel):
    """Typed collection dashboard response."""

    item: CollectionDashboard


class CollectionDashboardQueryFilters(BaseModel):
    """Query filters applied to collection dashboard listing endpoints."""

    only_stale: bool = False
    only_unhealthy: bool = False
    only_missing_bundle: bool = False
    only_missing_run: bool = False
    missing_workflow: str | None = None
    owner: str | None = None
    disease_area: str | None = None
    sort_by: Literal["activity", "health", "coverage", "name"] = "activity"
    group_by: Literal["owner", "disease_area"] | None = None
    top: int | None = None
    limit: int = 50
    timeline_limit: int = 10


class CollectionDashboardGroupSummary(BaseModel):
    """One grouped rollup inside the dashboard list response."""

    key: str
    label: str
    total: int
    stale: int = 0
    unhealthy: int = 0


class CollectionDashboardAggregateSummary(BaseModel):
    """Aggregate dashboard list summary for project inventory views."""

    total: int
    stale: int = 0
    unhealthy: int = 0
    missing_preferred: int = 0
    missing_bundle: int = 0
    missing_run: int = 0
    with_bundle: int = 0
    with_run: int = 0
    grouped_by: Literal["owner", "disease_area"] | None = None
    groups: list[CollectionDashboardGroupSummary] = Field(default_factory=list)


class CollectionDashboardListResponse(BaseModel):
    """Typed collection dashboard list response."""

    items: list[CollectionDashboard]
    total: int
    summary: CollectionDashboardAggregateSummary
    filters: CollectionDashboardQueryFilters


def artifact_record_from_dict(record: dict[str, Any]) -> ArtifactRecord:
    """Validate one artifact record."""
    return _ARTIFACT_RECORD_ADAPTER.validate_python(record)


def artifact_records_from_dicts(records: list[dict[str, Any]]) -> list[ArtifactRecord]:
    """Validate a list of artifact records."""
    return _ARTIFACT_RECORD_LIST_ADAPTER.validate_python(records)


def collection_manifest_from_dict(record: dict[str, Any]) -> CollectionManifest:
    """Validate one collection manifest."""
    return CollectionManifest.model_validate(record)


def collection_record_from_dict(record: dict[str, Any]) -> CollectionRecord:
    """Validate one collection record."""
    return CollectionRecord.model_validate(record)


def collection_records_from_dicts(records: list[dict[str, Any]]) -> list[CollectionRecord]:
    """Validate a list of collection records."""
    return [collection_record_from_dict(record) for record in records]


def research_run_record_from_dict(record: dict[str, Any]) -> ResearchRunRecord:
    """Validate one research run record."""
    return _RUN_RECORD_ADAPTER.validate_python(record)


def research_run_records_from_dicts(records: list[dict[str, Any]]) -> list[ResearchRunRecord]:
    """Validate a list of research run records."""
    return _RUN_RECORD_LIST_ADAPTER.validate_python(records)


def research_timeline_record_from_dict(record: dict[str, Any]) -> ResearchTimelineRecord:
    """Validate one research timeline record."""
    return _TIMELINE_RECORD_ADAPTER.validate_python(record)


def research_timeline_records_from_dicts(records: list[dict[str, Any]]) -> list[ResearchTimelineRecord]:
    """Validate a list of research timeline records."""
    return _TIMELINE_RECORD_LIST_ADAPTER.validate_python(records)
