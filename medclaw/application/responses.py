"""Application-layer response builders for typed CLI/API outputs."""

from __future__ import annotations

from medclaw.application.query_models import (
    ConfigResponse,
    ConfigSummary,
    ProviderListResponse,
    ProviderResponse,
    ProviderSummary,
    SkillListResponse,
    SkillSummary,
    WorkspaceResponse,
    WorkspaceSummary,
    WorkflowListResponse,
    WorkflowSummary,
)
from medclaw.evidence.api_models import (
    ArtifactRecord,
    ArtifactListResponse,
    ArtifactPayloadListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    CollectionListResponse,
    CollectionManifest,
    CollectionRecord,
    CollectionResponse,
    CollectionDashboard,
    CollectionDashboardResponse,
    ResearchRunListResponse,
    ResearchRunQueryFilters,
    ResearchRunRecord,
    ResearchRunResponse,
    ResearchTimelineListResponse,
    ResearchTimelineQueryFilters,
    ResearchTimelineRecord,
    ResearchReportListResponse,
    ResearchReportResponse,
)
from medclaw.evidence.models import ResearchReport, ResearchRun


def build_provider_summary(
    *,
    name: str,
    configured: bool,
    has_api_key: bool,
    base_url: str | None = None,
    organization: str | None = None,
    is_default: bool = False,
) -> ProviderSummary:
    """Build a typed provider summary."""
    return ProviderSummary(
        name=name,
        configured=configured,
        has_api_key=has_api_key,
        base_url=base_url,
        organization=organization,
        is_default=is_default,
    )


def build_provider_list_response(
    providers: list[ProviderSummary],
    *,
    default_provider: str,
) -> ProviderListResponse:
    """Build a typed provider listing response."""
    return ProviderListResponse(
        items=providers,
        total=len(providers),
        default_provider=default_provider,
    )


def build_provider_response(provider: ProviderSummary) -> ProviderResponse:
    """Build a typed single-provider response."""
    return ProviderResponse(item=provider)


def build_workspace_summary(
    *,
    path: str,
    exists: bool,
    skills_path: str,
    memory_path: str,
    reports_path: str,
    research_path: str,
    collections_path: str,
) -> WorkspaceSummary:
    """Build a typed workspace summary."""
    return WorkspaceSummary(
        path=path,
        exists=exists,
        skills_path=skills_path,
        memory_path=memory_path,
        reports_path=reports_path,
        research_path=research_path,
        collections_path=collections_path,
    )


def build_workspace_response(workspace: WorkspaceSummary) -> WorkspaceResponse:
    """Build a typed workspace response."""
    return WorkspaceResponse(item=workspace)


def build_config_response(
    *,
    config_path: str,
    workspace: WorkspaceSummary,
    default_provider: str,
    default_model: str,
    temperature: float,
    max_tokens: int,
    providers: list[ProviderSummary],
) -> ConfigResponse:
    """Build a typed config response."""
    return ConfigResponse(
        item=ConfigSummary(
            config_path=config_path,
            workspace=workspace,
            default_provider=default_provider,
            default_model=default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            providers=providers,
        )
    )


def build_research_report_response(report: ResearchReport) -> ResearchReportResponse:
    """Build a typed single-report response."""
    return ResearchReportResponse(report=report)


def build_research_report_list_response(reports: list[ResearchReport]) -> ResearchReportListResponse:
    """Build a typed multi-report response."""
    return ResearchReportListResponse(items=reports, total=len(reports))


def build_research_run_query_filters(
    *,
    query: str | None = None,
    collection: str | None = None,
    workflow_id: str | None = None,
    latest: bool = False,
    limit: int = 50,
) -> ResearchRunQueryFilters:
    """Build typed research run filter metadata."""
    return ResearchRunQueryFilters(
        query=query,
        collection=collection,
        workflow_id=workflow_id,
        latest=latest,
        limit=limit,
    )


def build_research_run_list_response(
    records: list[ResearchRunRecord],
    filters: ResearchRunQueryFilters,
) -> ResearchRunListResponse:
    """Build a typed research run list response."""
    return ResearchRunListResponse(items=records, total=len(records), filters=filters)


def build_research_run_response(
    *,
    target: str,
    path: str,
    record: ResearchRunRecord,
    run: ResearchRun,
) -> ResearchRunResponse:
    """Build a typed research run payload response."""
    return ResearchRunResponse(target=target, path=path, record=record, run=run)


def build_research_timeline_query_filters(
    *,
    query: str | None = None,
    collection: str | None = None,
    workflow_id: str | None = None,
    limit: int = 50,
) -> ResearchTimelineQueryFilters:
    """Build typed research timeline filter metadata."""
    return ResearchTimelineQueryFilters(
        query=query,
        collection=collection,
        workflow_id=workflow_id,
        limit=limit,
    )


def build_research_timeline_list_response(
    records: list[ResearchTimelineRecord],
    filters: ResearchTimelineQueryFilters,
) -> ResearchTimelineListResponse:
    """Build a typed research timeline list response."""
    return ResearchTimelineListResponse(items=records, total=len(records), filters=filters)


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
    records: list[ArtifactRecord],
    filters: ArtifactQueryFilters,
) -> ArtifactListResponse:
    """Build a typed artifact list response."""
    return ArtifactListResponse(
        items=records,
        total=len(records),
        filters=filters,
    )


def build_artifact_payload_response(
    *,
    target: str,
    artifact: str,
    record: ArtifactRecord | None,
    path: str,
    payload,
) -> ArtifactPayloadResponse:
    """Build a typed resolved artifact payload response."""
    if artifact == "report":
        payload = ResearchReport.model_validate(payload)
    return ArtifactPayloadResponse(
        target=target,
        artifact=artifact,
        kind=record.kind if record else "",
        path=path,
        format="markdown" if artifact == "bundle_markdown" else "json",
        record=record,
        payload=payload,
    )


def build_artifact_payload_list_response(
    items: list[ArtifactPayloadResponse],
    *,
    filters: ArtifactQueryFilters | None = None,
) -> ArtifactPayloadListResponse:
    """Build a typed resolved artifact payload list response."""
    return ArtifactPayloadListResponse(items=items, total=len(items), filters=filters)


def build_collection_list_response(
    records: list[CollectionRecord],
    *,
    limit: int,
) -> CollectionListResponse:
    """Build a typed collection list response."""
    return CollectionListResponse(
        items=records,
        total=len(records),
        limit=limit,
    )


def build_collection_response(record: CollectionRecord | CollectionManifest) -> CollectionResponse:
    """Build a typed single collection response."""
    return CollectionResponse(item=record)


def build_collection_dashboard_response(dashboard: CollectionDashboard) -> CollectionDashboardResponse:
    """Build a typed collection dashboard response."""
    return CollectionDashboardResponse(item=dashboard)


def build_workflow_summary(record: dict[str, str]) -> WorkflowSummary:
    """Build a typed workflow summary."""
    return WorkflowSummary.model_validate(record)


def build_workflow_list_response(records: list[WorkflowSummary]) -> WorkflowListResponse:
    """Build a typed workflow listing response."""
    return WorkflowListResponse(items=records, total=len(records))


def build_skill_summary(record: dict[str, str]) -> SkillSummary:
    """Build a typed skill summary."""
    return SkillSummary.model_validate(record)


def build_skill_list_response(
    records: list[SkillSummary],
    *,
    query: str | None = None,
) -> SkillListResponse:
    """Build a typed skill listing/search response."""
    return SkillListResponse(items=records, total=len(records), query=query)
