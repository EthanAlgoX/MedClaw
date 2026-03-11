"""Application-layer response builders for typed CLI/API outputs."""

from __future__ import annotations

from medclaw.evidence.api_models import (
    ArtifactListResponse,
    ArtifactPayloadListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    CollectionListResponse,
    CollectionManifest,
    CollectionRecord,
    CollectionResponse,
    ResearchReportListResponse,
    ResearchReportResponse,
    artifact_record_from_dict,
    artifact_records_from_dicts,
)
from medclaw.evidence.models import ResearchReport


def build_research_report_response(report: ResearchReport) -> ResearchReportResponse:
    """Build a typed single-report response."""
    return ResearchReportResponse(report=report)


def build_research_report_list_response(reports: list[ResearchReport]) -> ResearchReportListResponse:
    """Build a typed multi-report response."""
    return ResearchReportListResponse(items=reports, total=len(reports))


def build_artifact_query_filters(
    *,
    query: str | None = None,
    kind: str | None = None,
    workflow_id: str | None = None,
    collection: str | None = None,
    since: str | None = None,
    until: str | None = None,
    latest: bool = False,
    latest_by_collection: bool = False,
    limit: int = 50,
) -> ArtifactQueryFilters:
    """Build typed artifact filter metadata."""
    return ArtifactQueryFilters(
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


def build_artifact_list_response(
    records: list[dict],
    filters: ArtifactQueryFilters,
) -> ArtifactListResponse:
    """Build a typed artifact list response."""
    return ArtifactListResponse(
        items=artifact_records_from_dicts(records),
        total=len(records),
        filters=filters,
    )


def build_artifact_payload_response(
    *,
    target: str,
    artifact: str,
    record: dict | None,
    path: str,
    payload,
) -> ArtifactPayloadResponse:
    """Build a typed resolved artifact payload response."""
    if artifact == "report":
        payload = ResearchReport.model_validate(payload)
    return ArtifactPayloadResponse(
        target=target,
        artifact=artifact,
        kind=record["kind"] if record else "",
        path=path,
        format="markdown" if artifact == "bundle_markdown" else "json",
        record=artifact_record_from_dict(record) if record else None,
        payload=payload,
    )


def build_artifact_payload_list_response(
    items: list[ArtifactPayloadResponse],
    *,
    filters: ArtifactQueryFilters | None = None,
) -> ArtifactPayloadListResponse:
    """Build a typed resolved artifact payload list response."""
    return ArtifactPayloadListResponse(items=items, total=len(items), filters=filters)


def build_collection_record(record: dict) -> CollectionRecord:
    """Build a typed collection registry record."""
    return CollectionRecord.model_validate(record)


def build_collection_list_response(
    records: list[dict],
    *,
    limit: int,
) -> CollectionListResponse:
    """Build a typed collection list response."""
    return CollectionListResponse(
        items=[build_collection_record(record) for record in records],
        total=len(records),
        limit=limit,
    )


def build_collection_response(record: dict) -> CollectionResponse:
    """Build a typed single collection response."""
    if {
        "report_count",
        "evidence_count",
        "citation_count",
        "workflows",
        "titles",
    }.issubset(record):
        item = CollectionRecord.model_validate(record)
    else:
        item = CollectionManifest.model_validate(record)
    return CollectionResponse(item=item)
