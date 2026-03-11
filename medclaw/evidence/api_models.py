"""Typed response models for research artifact APIs."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport


class ResearchReportResponse(BaseModel):
    """Typed single-report response."""

    report: ResearchReport


class ResearchReportListResponse(BaseModel):
    """Typed multi-report response."""

    items: list[ResearchReport]
    total: int


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


def artifact_record_from_dict(record: dict[str, Any]) -> ArtifactRecord:
    """Validate one artifact record."""
    return _ARTIFACT_RECORD_ADAPTER.validate_python(record)


def artifact_records_from_dicts(records: list[dict[str, Any]]) -> list[ArtifactRecord]:
    """Validate a list of artifact records."""
    return _ARTIFACT_RECORD_LIST_ADAPTER.validate_python(records)
