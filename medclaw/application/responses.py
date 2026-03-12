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
    CollectionDashboardAggregateSummary,
    CollectionDashboardGroupSummary,
    CollectionDashboardResponse,
    CollectionDashboardListResponse,
    CollectionDashboardQueryFilters,
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


def build_collection_dashboard_query_filters(
    *,
    query: str | None = None,
    only_stale: bool = False,
    stale_days_min: int | None = None,
    only_unhealthy: bool = False,
    only_missing_bundle: bool = False,
    only_missing_run: bool = False,
    missing_workflow: str | None = None,
    owner: str | None = None,
    disease_area: str | None = None,
    sort_by: str = "activity",
    group_by: str | None = None,
    top: int | None = None,
    limit: int = 50,
    timeline_limit: int = 10,
) -> CollectionDashboardQueryFilters:
    """Build typed collection dashboard filter metadata."""
    return CollectionDashboardQueryFilters(
        query=query,
        only_stale=only_stale,
        stale_days_min=stale_days_min,
        only_unhealthy=only_unhealthy,
        only_missing_bundle=only_missing_bundle,
        only_missing_run=only_missing_run,
        missing_workflow=missing_workflow,
        owner=owner,
        disease_area=disease_area,
        sort_by=sort_by,
        group_by=group_by,
        top=top,
        limit=limit,
        timeline_limit=timeline_limit,
    )


def build_collection_dashboard_list_response(
    dashboards: list[CollectionDashboard],
    filters: CollectionDashboardQueryFilters,
) -> CollectionDashboardListResponse:
    """Build a typed collection dashboard list response."""
    return CollectionDashboardListResponse(
        items=dashboards,
        total=len(dashboards),
        summary=build_collection_dashboard_aggregate_summary(dashboards, group_by=filters.group_by),
        filters=filters,
    )


def build_collection_dashboard_aggregate_summary(
    dashboards: list[CollectionDashboard],
    *,
    group_by: str | None = None,
) -> CollectionDashboardAggregateSummary:
    """Build an aggregate summary for dashboard list views."""
    groups: dict[str, CollectionDashboardGroupSummary] = {}
    stale = 0
    unhealthy = 0
    missing_preferred = 0
    missing_bundle = 0
    missing_run = 0
    with_bundle = 0
    with_run = 0

    for dashboard in dashboards:
        if dashboard.stale:
            stale += 1
        if dashboard.health_signals:
            unhealthy += 1
        if dashboard.missing_preferred_workflows:
            missing_preferred += 1
        if dashboard.latest_bundle is not None:
            with_bundle += 1
        else:
            missing_bundle += 1
        if dashboard.latest_run is not None:
            with_run += 1
        else:
            missing_run += 1

        if group_by:
            if group_by == "owner":
                raw_label = dashboard.collection.owner.strip()
            else:
                raw_label = dashboard.collection.disease_area.strip()
            label = raw_label or "Unspecified"
            key = label.lower()
            group = groups.setdefault(
                key,
                CollectionDashboardGroupSummary(key=key, label=label, total=0, stale=0, unhealthy=0),
            )
            group.total += 1
            if dashboard.stale:
                group.stale += 1
            if dashboard.health_signals:
                group.unhealthy += 1

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (group.total, group.unhealthy, group.label.lower()),
        reverse=True,
    )
    return CollectionDashboardAggregateSummary(
        total=len(dashboards),
        stale=stale,
        unhealthy=unhealthy,
        missing_preferred=missing_preferred,
        missing_bundle=missing_bundle,
        missing_run=missing_run,
        with_bundle=with_bundle,
        with_run=with_run,
        grouped_by=group_by,
        groups=ordered_groups,
    )


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
