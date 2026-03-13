"""Shared CLI helpers and runtime wiring."""

from __future__ import annotations

import json
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown

from medclaw.application import (
    MedicalResearchUseCases,
    build_artifact_list_response,
    build_artifact_payload_list_response,
    build_artifact_payload_response,
    build_collection_dashboard_response,
    build_collection_response,
    build_config_response,
    build_export_summary,
    build_provider_summary,
    build_research_report_list_response,
    build_research_report_response,
    build_workspace_summary,
)
from medclaw.config.loader import (
    ensure_workspace,
    get_default_config_path,
    get_workspace_path,
    load_config,
)
from medclaw.config.schema import ProviderConfig
from medclaw.evidence.api_models import (
    ArtifactRecord,
    CollectionDashboard,
    CollectionDashboardAggregateSummary,
    CollectionDashboardQueryFilters,
    CollectionBundleArtifactRecord,
    CollectionRecord,
    ResearchRunRecord,
    ResearchTimelineRecord,
)
from medclaw.evidence.artifacts import (
    CLI_ARTIFACTS,
    CLI_ARTIFACT_HELP,
    artifact_choices_for_kind,
    build_unsupported_artifact_error,
    normalize_artifact_name,
)
from medclaw.evidence.models import ResearchReport, ResearchRun
from medclaw.evidence.store import EvidenceStore
from medclaw.application.query_models import ExportSummary
from medclaw.providers.deepseek import DeepSeekProvider
from medclaw.providers.openrouter import OpenRouterProvider

console = Console()

SUPPORTED_PROVIDERS = ("openai", "anthropic", "openrouter", "deepseek", "google")

RUNTIME_PROVIDER_MODELS = {
    "openrouter": OpenRouterProvider.MODELS,
    "deepseek": DeepSeekProvider.MODELS,
}

RUNTIME_PROVIDER_DEFAULT_MODELS = {
    "openrouter": OpenRouterProvider.DEFAULT_MODEL,
    "deepseek": DeepSeekProvider.DEFAULT_MODEL,
}


def get_provider(config):
    """Get the configured LLM provider instance."""
    provider_name = config.agents.defaults.provider

    if provider_name == "deepseek":
        provider_config = config.providers.deepseek
        if provider_config and provider_config.apiKey:
            return DeepSeekProvider(
                api_key=provider_config.apiKey,
                base_url=provider_config.baseUrl or "https://api.deepseek.com",
            )

    if provider_name == "openrouter":
        provider_config = config.providers.openrouter
        if provider_config and provider_config.apiKey:
            return OpenRouterProvider(
                api_key=provider_config.apiKey,
                base_url=provider_config.baseUrl or "https://openrouter.ai/api/v1",
            )

    raise ValueError(f"Provider {provider_name} not configured or not available")


def get_research_use_cases() -> MedicalResearchUseCases:
    """Create research use cases for the configured workspace."""
    workspace = get_workspace_path()
    ensure_workspace(workspace)
    return MedicalResearchUseCases(workspace)


def get_evidence_store() -> EvidenceStore:
    """Create an evidence store for the configured workspace."""
    workspace = get_workspace_path()
    ensure_workspace(workspace)
    return EvidenceStore(workspace)


def get_configured_provider():
    """Create the configured provider or exit with a readable message."""
    config = load_config()
    try:
        return config, get_provider(config)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("Run 'medclaw onboard' to set up your configuration")
        raise typer.Exit(1)


def build_workspace_summary_model():
    """Build a typed workspace summary from the configured workspace layout."""
    workspace = get_workspace_path()
    return build_workspace_summary(
        path=str(workspace),
        exists=workspace.exists(),
        skills_path=str(workspace / "skills"),
        memory_path=str(workspace / "memory"),
        reports_path=str(workspace / "reports"),
        research_path=str(workspace / "research"),
        collections_path=str(workspace / "research" / "collections"),
        exports_path=str(workspace / "research" / "exports"),
    )


def get_research_exports_dir() -> Path:
    """Return the workspace-scoped export directory for research views."""
    workspace = get_workspace_path()
    ensure_workspace(workspace)
    return workspace / "research" / "exports"


def build_provider_summaries(config) -> list:
    """Build typed provider summaries from config."""
    return [load_provider_summary(config, name) for name in SUPPORTED_PROVIDERS]


def build_config_response_model(config):
    """Build a typed config response for the current config state."""
    workspace_summary = build_workspace_summary_model()
    providers = build_provider_summaries(config)
    return build_config_response(
        config_path=str(get_default_config_path()),
        workspace=workspace_summary,
        default_provider=config.agents.defaults.provider,
        default_model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.maxTokens,
        providers=providers,
    )


def emit_config_response(config, *, as_json: bool) -> None:
    """Render a config response in text or JSON form."""
    response = build_config_response_model(config)
    if as_json:
        write_json(response)
        return

    console.print("[bold]Config updated:[/bold]")
    console.print(f"default provider: {response.item.default_provider}")
    console.print(f"default model: {response.item.default_model}")
    console.print(f"temperature: {response.item.temperature}")
    console.print(f"max tokens: {response.item.max_tokens}")
    console.print(f"workspace: {response.item.workspace.path}")


def ensure_supported_provider_name(name: str) -> None:
    """Exit with a readable error when the provider name is unsupported."""
    if name not in SUPPORTED_PROVIDERS:
        choices = ", ".join(SUPPORTED_PROVIDERS)
        console.print(f"[red]Error:[/red] Unsupported provider. Choose from: {choices}")
        raise typer.Exit(1)


def load_provider_config(config, name: str) -> ProviderConfig | None:
    """Return one provider config after validating the provider name."""
    ensure_supported_provider_name(name)
    return getattr(config.providers, name, None)


def load_provider_summary(config, name: str):
    """Build one provider summary from the current config."""
    provider = load_provider_config(config, name)
    return build_provider_summary(
        name=name,
        configured=provider is not None,
        has_api_key=bool(provider and provider.apiKey),
        base_url=provider.baseUrl if provider else None,
        organization=provider.organization if provider else None,
        is_default=config.agents.defaults.provider == name,
    )


def ensure_provider_has_api_key(name: str, provider: ProviderConfig | None) -> None:
    """Require an API key before a provider can become the default."""
    if provider is None or not provider.apiKey:
        console.print(f"[red]Error:[/red] Provider '{name}' must have an API key before it can become the default.")
        raise typer.Exit(1)


def ensure_runtime_supported_provider(name: str) -> None:
    """Require a provider that MedClaw can instantiate at runtime."""
    if name not in RUNTIME_PROVIDER_MODELS:
        runtime_choices = ", ".join(sorted(RUNTIME_PROVIDER_MODELS))
        console.print(
            f"[red]Error:[/red] Provider '{name}' is not available as a runtime provider yet. Choose from: {runtime_choices}"
        )
        raise typer.Exit(1)


def ensure_model_compatible_with_provider(provider_name: str, model: str) -> None:
    """Validate the model against the runtime catalog for the selected provider."""
    supported_models = RUNTIME_PROVIDER_MODELS.get(provider_name)
    if supported_models is None:
        return
    if model not in supported_models:
        choices = ", ".join(supported_models)
        console.print(
            f"[red]Error:[/red] Model '{model}' is not compatible with provider '{provider_name}'. Supported models: {choices}"
        )
        raise typer.Exit(1)


def normalize_default_model_for_provider(config, provider_name: str) -> str | None:
    """Reset the default model when switching providers across incompatible catalogs."""
    default_model = config.agents.defaults.model
    supported_models = RUNTIME_PROVIDER_MODELS.get(provider_name)
    if supported_models is None or default_model in supported_models:
        return None
    replacement_model = RUNTIME_PROVIDER_DEFAULT_MODELS[provider_name]
    config.agents.defaults.model = replacement_model
    return replacement_model


def choose_replacement_default(config, *, removed_provider: str) -> str | None:
    """Pick another configured provider with an API key as the replacement default."""
    for candidate in SUPPORTED_PROVIDERS:
        if candidate == removed_provider:
            continue
        provider = getattr(config.providers, candidate, None)
        if provider and provider.apiKey:
            return candidate
    return None


async def run_research_workflow_report(
    workflow_id: str,
    query: str,
    no_llm: bool = False,
    collection: str | None = None,
) -> ResearchReport:
    """Run a typed research workflow with optional LLM synthesis disabled."""
    use_cases = get_research_use_cases()
    provider = None
    if not no_llm:
        _, provider = get_configured_provider()
    return await use_cases.run_workflow_report(
        workflow_id=workflow_id,
        query=query,
        provider=provider,
        collection=collection,
    )


def emit_research_report(
    report: ResearchReport,
    as_json: bool = False,
    save_path_only: bool = False,
) -> None:
    """Render a research report for CLI output."""
    saved_path = report.metadata.get("saved_path", "")
    if save_path_only:
        console.print(str(saved_path))
        return
    if as_json:
        write_json(build_research_report_response(report))
        return
    from medclaw.reporting.briefs import render_research_report

    console.print(Markdown(render_research_report(report)))


def emit_research_reports(
    reports: list[ResearchReport],
    as_json: bool = False,
    save_path_only: bool = False,
) -> None:
    """Render one or more research reports for CLI output."""
    if save_path_only:
        for report in reports:
            console.print(str(report.metadata.get("saved_path", "")))
        bundle_saved_path = reports[0].metadata.get("bundle_saved_path", "") if reports else ""
        if bundle_saved_path:
            console.print(str(bundle_saved_path))
        return
    if as_json:
        write_json(build_research_report_list_response(reports))
        return

    if len(reports) > 1:
        from medclaw.reporting.briefs import render_collection_report_bundle

        console.print(Markdown(render_collection_report_bundle(reports)))
        bundle_saved_path = reports[0].metadata.get("bundle_saved_path", "")
        if bundle_saved_path:
            console.print(f"\nBundle summary saved to: {bundle_saved_path}")
        return

    emit_research_report(reports[0])


def write_json(payload) -> None:
    """Write machine-readable JSON without terminal wrapping."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


def save_json(payload, path: str | Path) -> Path:
    """Persist a machine-readable JSON payload to disk."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    target_path = Path(path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target_path


def save_text(text: str, path: str | Path) -> Path:
    """Persist plain text or markdown to disk."""
    target_path = Path(path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(text, encoding="utf-8")
    return target_path


def resolve_export_path(path: str | Path) -> Path:
    """Resolve relative export paths under the workspace export directory."""
    target_path = Path(path).expanduser()
    if target_path.is_absolute():
        return target_path
    return get_research_exports_dir() / target_path


def _yaml_frontmatter_lines(value: Any, *, indent: int = 0) -> list[str]:
    """Render a small YAML-compatible frontmatter payload."""
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_frontmatter_lines(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}{key}: {json.dumps(item, ensure_ascii=False)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_frontmatter_lines(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}- {json.dumps(item, ensure_ascii=False)}")
        return lines
    return [f"{prefix}{json.dumps(value, ensure_ascii=False)}"]


def build_dashboard_export_artifact_id(
    dashboards: list[CollectionDashboard],
    *,
    sort_by: str,
    summary_only: bool,
    group_by: str | None,
    filters: CollectionDashboardQueryFilters | None,
) -> str:
    """Build a deterministic export id for dashboard markdown artifacts."""
    payload = {
        "collections": [dashboard.collection.slug for dashboard in dashboards],
        "sort_by": sort_by,
        "summary_only": summary_only,
        "group_by": group_by,
        "filters": filters.model_dump(mode="json") if filters is not None else None,
    }
    digest = hashlib.sha1(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"dashboard-inventory-{digest[:12]}"


def _parse_markdown_frontmatter(path: Path) -> dict[str, str]:
    """Parse shallow frontmatter keys from markdown exports."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    metadata: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line == "---":
            break
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                metadata[key] = json.loads(value)
            except json.JSONDecodeError:
                metadata[key] = value.strip('"')
        else:
            metadata[key] = value
    return metadata


def _infer_export_kind(path: Path) -> str:
    """Infer export kind from content or extension."""
    if path.suffix == ".md":
        return _parse_markdown_frontmatter(path).get("kind", "markdown_export")
    if path.suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return "json_export"
        if isinstance(payload, dict) and {"items", "summary", "filters"} <= payload.keys():
            return "collection_dashboard_inventory"
        return "json_export"
    return "export"


def _export_artifact_id(path: Path) -> str:
    """Resolve a stable export id from frontmatter or filename."""
    if path.suffix == ".md":
        artifact_id = _parse_markdown_frontmatter(path).get("artifact_id")
        if artifact_id:
            return artifact_id
    return path.stem


def _export_generated_at(path: Path) -> str:
    """Resolve export generation time from content or filesystem metadata."""
    if path.suffix == ".md":
        generated_at = _parse_markdown_frontmatter(path).get("generated_at")
        if generated_at:
            return generated_at
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def list_export_summaries(
    *,
    query: str | None = None,
    kind: str | None = None,
    latest: bool = False,
    limit: int = 20,
) -> list[ExportSummary]:
    """List exports saved under the workspace export directory."""
    exports_dir = get_research_exports_dir()
    lowered = query.lower().strip() if query else ""
    normalized_kind = kind.strip().lower() if kind else ""
    items: list[ExportSummary] = []
    for path in sorted(exports_dir.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        export_kind = _infer_export_kind(path)
        export_format = path.suffix.lstrip(".") or "file"
        if normalized_kind and normalized_kind not in {export_kind.lower(), export_format.lower()}:
            continue
        artifact_id = _export_artifact_id(path)
        if lowered:
            haystack = " ".join([path.name, export_kind, artifact_id]).lower()
            if lowered not in haystack:
                continue
        items.append(
            build_export_summary(
                {
                    "id": artifact_id,
                    "path": str(path),
                    "filename": path.name,
                    "format": export_format,
                    "export_kind": export_kind,
                    "artifact_id": artifact_id,
                    "generated_at": _export_generated_at(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        )
        if latest:
            return items[:1]
        if len(items) >= limit:
            break
    return items


def get_export_summary(target: str) -> ExportSummary:
    """Resolve one workspace export by id, filename, or path."""
    exports_dir = get_research_exports_dir()
    target_path = Path(target).expanduser()
    if not target_path.is_absolute():
        target_path = exports_dir / target_path
    target_path = target_path.resolve()

    for record in list_export_summaries(limit=10_000):
        record_path = Path(record.path).resolve()
        if target in {record.id, record.artifact_id, record.filename, record.path}:
            return record
        if target_path == record_path:
            return record

    raise FileNotFoundError(f"Export '{target}' was not found in {exports_dir}")


def read_export_payload(record: ExportSummary) -> object:
    """Read one export payload based on its format."""
    path = Path(record.path)
    if record.format == "json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def emit_artifact_record(record: ArtifactRecord, store: EvidenceStore) -> None:
    """Render a single artifact record into user-facing output."""
    if isinstance(record, CollectionBundleArtifactRecord):
        markdown = store.read_bundle_artifact(record.id, artifact="bundle_markdown")
        console.print(Markdown(markdown))
        return

    payload = store.read_artifact(record.id, artifact="report")
    report_model = ResearchReport.model_validate(payload)
    emit_research_report(report_model)


def normalize_artifact_option(artifact: str | None) -> str | None:
    """Normalize CLI artifact option names."""
    return normalize_artifact_name(artifact, choices=CLI_ARTIFACTS)


def artifact_paths_for_record(record: ArtifactRecord, store: EvidenceStore) -> dict[str, Path]:
    """Return the artifact path bundle for a unified artifact record."""
    if isinstance(record, CollectionBundleArtifactRecord):
        return store.get_bundle_artifact_paths(record.id)
    return store.get_artifact_paths(record.id)


def artifact_payload_for_record(record: ArtifactRecord, store: EvidenceStore, artifact: str):
    """Read a specific artifact payload for a unified artifact record."""
    supported = artifact_choices_for_kind(record.kind)
    if artifact not in supported:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    if isinstance(record, CollectionBundleArtifactRecord):
        return store.read_bundle_artifact(record.id, artifact=artifact)
    return store.read_artifact(record.id, artifact=artifact)


def artifact_path_for_record(record: ArtifactRecord, store: EvidenceStore, artifact: str) -> str:
    """Resolve a specific artifact path for a unified artifact record."""
    supported = artifact_choices_for_kind(record.kind)
    if artifact not in supported:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    paths = artifact_paths_for_record(record, store)
    if artifact not in paths:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    return str(paths[artifact])


def artifact_primary_path(record: ArtifactRecord) -> str:
    """Return the primary file path for an artifact record."""
    if isinstance(record, CollectionBundleArtifactRecord):
        return record.bundle_markdown_path
    return record.path


def read_show_artifact(store: EvidenceStore, target: str, artifact: str) -> tuple[str, object]:
    """Read a report or bundle artifact for the show command."""
    normalized_artifact = normalize_artifact_option(artifact) or "report"
    if normalized_artifact in {"bundle_markdown", "bundle_json"}:
        return normalized_artifact, store.read_bundle_artifact(target, artifact=normalized_artifact)

    if normalized_artifact in {"evidence", "citations"}:
        return normalized_artifact, store.read_artifact(target, artifact=normalized_artifact)

    try:
        return normalized_artifact, store.read_artifact(target, artifact=normalized_artifact)
    except (FileNotFoundError, ValueError) as report_error:
        bundle_artifact = "bundle_markdown" if normalized_artifact == "report" else normalized_artifact
        try:
            return bundle_artifact, store.read_bundle_artifact(target, artifact=bundle_artifact)
        except (FileNotFoundError, ValueError):
            raise report_error


def write_lines(lines: list[str]) -> None:
    """Write plain lines without terminal wrapping."""
    for line in lines:
        sys.stdout.write(line)
        sys.stdout.write("\n")


def emit_artifact_record_list(records: list[ArtifactRecord]) -> None:
    """Render a compact list of artifact records."""
    if not records:
        console.print("[yellow]No research artifacts matched the current filters.[/yellow]")
        return

    console.print("[bold]Latest Research Artifacts:[/bold]")
    for record in records:
        generated_at = record.generated_at.split("T", 1)[0]
        if isinstance(record, CollectionBundleArtifactRecord):
            console.print(
                f"  - {record.collection} [bundle] {generated_at} workflows={', '.join(record.workflow_ids)}"
            )
        else:
            console.print(
                f"  - {record.title} [{record.workflow_id}] {generated_at}"
            )


def emit_report_summary(report: ResearchReport) -> None:
    """Render a compact summary view for saved reports."""
    generated_at = report.generated_at.split("T", 1)[0]
    console.print(f"[bold]{report.title}[/bold]")
    console.print(f"workflow: {report.workflow_id}")
    if report.metadata.get("collection"):
        console.print(f"collection: {report.metadata['collection']}")
    if report.metadata.get("collection_objective"):
        console.print(f"objective: {report.metadata['collection_objective']}")
    console.print(f"generated: {generated_at}")
    console.print(f"question: {report.question}")
    console.print(f"evidence: {len(report.evidence)}")
    if report.key_findings:
        console.print("key findings:")
        for finding in report.key_findings[:5]:
            console.print(f"  - {finding}")
    elif report.summary:
        console.print(f"summary: {' '.join(report.summary.split())}")


def emit_collection_manifest(record: CollectionRecord) -> None:
    """Render a collection manifest with aggregate report stats."""
    latest = record.latest_activity_at.split("T", 1)[0] if record.latest_activity_at else "n/a"
    console.print(f"[bold]{record.collection}[/bold]")
    console.print(f"slug: {record.slug}")
    console.print(f"reports: {record.report_count}")
    console.print(f"latest: {latest}")
    if record.stale_days is not None:
        stale_label = "yes" if record.stale else "no"
        console.print(f"stale: {stale_label} ({record.stale_days} days)")
    if record.owner:
        console.print(f"owner: {record.owner}")
    if record.disease_area:
        console.print(f"disease area: {record.disease_area}")
    if record.objective:
        console.print(f"objective: {record.objective}")
    if record.tags:
        console.print(f"tags: {', '.join(record.tags)}")
    if record.preferred_workflows:
        console.print(f"preferred workflows: {', '.join(record.preferred_workflows)}")
    if record.missing_preferred_workflows:
        console.print(f"missing preferred workflows: {', '.join(record.missing_preferred_workflows)}")
    if record.workflows:
        console.print(f"active workflows: {', '.join(record.workflows)}")
    if record.latest_bundle_markdown_path:
        console.print(f"latest bundle: {record.latest_bundle_markdown_path}")
    if record.latest_run_id:
        console.print(f"latest run: {record.latest_run_id}")
    if record.health_signals:
        console.print(f"health signals: {', '.join(record.health_signals)}")


def emit_collection_dashboard(
    dashboard: CollectionDashboard,
    *,
    as_json: bool = False,
) -> None:
    """Render one collection dashboard in text or JSON form."""
    if as_json:
        write_json(build_collection_dashboard_response(dashboard))
        return

    record = dashboard.collection
    console.print(f"[bold]{record.collection}[/bold]")
    console.print(f"slug: {record.slug}")
    console.print(f"reports: {record.report_count}")
    console.print(f"workflows covered: {', '.join(dashboard.covered_workflows) or 'n/a'}")
    if dashboard.latest_activity_at:
        console.print(f"latest activity: {dashboard.latest_activity_at.split('T', 1)[0]}")
    if dashboard.stale:
        console.print(f"stale: yes ({dashboard.stale_days} days)")
    elif dashboard.stale_days is not None:
        console.print(f"stale: no ({dashboard.stale_days} days)")
    if record.objective:
        console.print(f"objective: {record.objective}")
    if record.owner:
        console.print(f"owner: {record.owner}")
    if record.preferred_workflows:
        console.print(f"preferred workflows: {', '.join(record.preferred_workflows)}")
    if dashboard.missing_preferred_workflows:
        console.print(
            f"missing preferred workflows: {', '.join(dashboard.missing_preferred_workflows)}"
        )
    if dashboard.health_signals:
        console.print(f"health signals: {', '.join(dashboard.health_signals)}")
    if dashboard.latest_report is not None:
        console.print(f"latest report: {dashboard.latest_report.title}")
    if dashboard.latest_bundle is not None:
        console.print(f"latest bundle: {dashboard.latest_bundle.path}")
    if dashboard.latest_run is not None:
        console.print(f"latest run: {dashboard.latest_run.id} ({dashboard.latest_run.scope})")
    if dashboard.timeline:
        console.print("recent timeline:")
        for timeline_record in dashboard.timeline[:5]:
            event_date = timeline_record.timestamp.split("T", 1)[0] if timeline_record.timestamp else "n/a"
            console.print(f"  - {event_date} ({timeline_record.kind}) {timeline_record.title}")


def emit_collection_dashboard_list(
    dashboards: list[CollectionDashboard],
    *,
    sort_by: str = "activity",
    summary_only: bool = False,
    group_by: str | None = None,
    summary: CollectionDashboardAggregateSummary | None = None,
) -> None:
    """Render a compact multi-collection dashboard view."""
    if not dashboards:
        console.print("[yellow]No collection dashboards matched the current filters.[/yellow]")
        return

    if summary is not None:
        summary_line = (
            f"total={summary.total} stale={summary.stale} unhealthy={summary.unhealthy} "
            f"missing_preferred={summary.missing_preferred} missing_bundle={summary.missing_bundle} "
            f"missing_run={summary.missing_run} with_bundle={summary.with_bundle} "
            f"with_run={summary.with_run}"
        )
        console.print(f"[bold]Collection Dashboards[/bold] (sort={sort_by}): {summary_line}")
        if summary.groups:
            grouped_label = "disease area" if summary.grouped_by == "disease_area" else summary.grouped_by
            console.print(f"grouped by {grouped_label}:")
            for group in summary.groups:
                console.print(
                    "  - "
                    f"{group.label} total={group.total} stale={group.stale} unhealthy={group.unhealthy}"
                )
    else:
        console.print(f"[bold]Collection Dashboards[/bold] (sort={sort_by}):")

    current_group: str | None = None
    for dashboard in dashboards:
        record = dashboard.collection
        group_label = None
        if group_by == "owner":
            group_label = record.owner or "Unspecified"
        elif group_by == "disease_area":
            group_label = record.disease_area or "Unspecified"
        if group_label != current_group and group_by:
            console.print(f"[cyan]{group_label}[/cyan]")
            current_group = group_label
        latest = dashboard.latest_activity_at.split("T", 1)[0] if dashboard.latest_activity_at else "n/a"
        status = f"stale ({dashboard.stale_days} days)" if dashboard.stale else (
            f"active ({dashboard.stale_days} days)" if dashboard.stale_days is not None else "unknown"
        )
        console.print(
            "  - "
            f"{record.collection} latest={latest} status={status} "
            f"reports={record.report_count} workflows={len(dashboard.covered_workflows)}"
        )
        if summary_only:
            if dashboard.health_signals:
                console.print(f"      health: {', '.join(dashboard.health_signals)}")
            continue
        if dashboard.latest_run is not None:
            console.print(f"      latest run: {dashboard.latest_run.id}")
        if dashboard.latest_report is not None:
            console.print(f"      latest report: {dashboard.latest_report.title}")
        if dashboard.latest_bundle is not None:
            console.print(f"      latest bundle: {dashboard.latest_bundle.path}")
        if dashboard.missing_preferred_workflows:
            console.print(
                f"      missing preferred: {', '.join(dashboard.missing_preferred_workflows)}"
            )
        if dashboard.health_signals:
            console.print(f"      health: {', '.join(dashboard.health_signals)}")


def render_collection_dashboard_list_markdown(
    dashboards: list[CollectionDashboard],
    *,
    sort_by: str = "activity",
    summary_only: bool = False,
    group_by: str | None = None,
    summary: CollectionDashboardAggregateSummary | None = None,
    filters: CollectionDashboardQueryFilters | None = None,
    workspace_path: str | None = None,
) -> str:
    """Render a markdown export for the collection dashboard list view."""
    frontmatter_payload = {
        "kind": "collection_dashboard_inventory",
        "artifact_id": build_dashboard_export_artifact_id(
            dashboards,
            sort_by=sort_by,
            summary_only=summary_only,
            group_by=group_by,
            filters=filters,
        ),
        "export_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_path": workspace_path,
        "sort_by": sort_by,
        "group_by": group_by,
        "summary_only": summary_only,
        "filters": filters.model_dump(mode="json") if filters is not None else None,
        "summary": summary.model_dump(mode="json") if summary is not None else None,
    }
    lines: list[str] = [
        "---",
        *_yaml_frontmatter_lines(frontmatter_payload),
        "---",
        "",
        "# Collection Dashboard Inventory",
        "",
    ]
    lines.append(f"- Sort by: `{sort_by}`")
    if summary_only:
        lines.append("- View: summary")
    if summary is not None:
        lines.append(f"- Total: {summary.total}")
        lines.append(f"- Stale: {summary.stale}")
        lines.append(f"- Unhealthy: {summary.unhealthy}")
        lines.append(f"- Missing preferred: {summary.missing_preferred}")
        lines.append(f"- Missing bundle: {summary.missing_bundle}")
        lines.append(f"- Missing run: {summary.missing_run}")
        lines.append(f"- With bundle: {summary.with_bundle}")
        lines.append(f"- With run: {summary.with_run}")
        if summary.grouped_by:
            grouped_label = "disease area" if summary.grouped_by == "disease_area" else summary.grouped_by
            lines.append(f"- Grouped by: {grouped_label}")
    lines.append("")

    if summary is not None and summary.groups:
        lines.append("## Groups")
        lines.append("")
        for group in summary.groups:
            lines.append(
                f"- {group.label}: total={group.total}, stale={group.stale}, unhealthy={group.unhealthy}"
            )
        lines.append("")

    current_group: str | None = None
    for dashboard in dashboards:
        record = dashboard.collection
        group_label = None
        if group_by == "owner":
            group_label = record.owner or "Unspecified"
        elif group_by == "disease_area":
            group_label = record.disease_area or "Unspecified"
        if group_label != current_group and group_by:
            lines.append(f"## {group_label}")
            lines.append("")
            current_group = group_label

        latest = dashboard.latest_activity_at.split("T", 1)[0] if dashboard.latest_activity_at else "n/a"
        status = f"stale ({dashboard.stale_days} days)" if dashboard.stale else (
            f"active ({dashboard.stale_days} days)" if dashboard.stale_days is not None else "unknown"
        )
        lines.append(f"### {record.collection}")
        lines.append("")
        lines.append(f"- Latest activity: {latest}")
        lines.append(f"- Status: {status}")
        lines.append(f"- Reports: {record.report_count}")
        lines.append(f"- Workflows covered: {len(dashboard.covered_workflows)}")
        if dashboard.health_signals:
            lines.append(f"- Health: {', '.join(dashboard.health_signals)}")
        if summary_only:
            lines.append("")
            continue
        if dashboard.latest_run is not None:
            lines.append(f"- Latest run: {dashboard.latest_run.id}")
        if dashboard.latest_report is not None:
            lines.append(f"- Latest report: {dashboard.latest_report.title}")
        if dashboard.latest_bundle is not None:
            lines.append(f"- Latest bundle: {dashboard.latest_bundle.path}")
        if dashboard.missing_preferred_workflows:
            lines.append(f"- Missing preferred: {', '.join(dashboard.missing_preferred_workflows)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def emit_research_run(run: ResearchRun) -> None:
    """Render a saved research run in a compact operator-friendly format."""
    started = run.started_at.split("T", 1)[0] if run.started_at else "n/a"
    completed = run.completed_at.split("T", 1)[0] if run.completed_at else "n/a"
    scope = "collection" if len(run.workflow_runs) > 1 else "workflow"
    console.print(f"[bold]Research Run {run.id}[/bold]")
    console.print(f"scope: {scope}")
    if run.collection:
        console.print(f"collection: {run.collection}")
    console.print(f"status: {run.status}")
    console.print(f"started: {started}")
    console.print(f"completed: {completed}")
    console.print(f"query: {run.query}")
    console.print(f"workflows: {', '.join(workflow_run.workflow_id for workflow_run in run.workflow_runs)}")
    if run.metadata.get("bundle_saved_path"):
        console.print(f"bundle: {run.metadata['bundle_saved_path']}")
    for workflow_run in run.workflow_runs:
        console.print(
            "  - "
            f"{workflow_run.workflow_id} "
            f"provider={workflow_run.provider_name or 'none'} "
            f"model={workflow_run.model_name or 'none'}"
        )
        if workflow_run.report_path:
            console.print(f"      report: {workflow_run.report_path}")


def emit_research_run_record_list(records: list[ResearchRunRecord]) -> None:
    """Render a compact list of research run records."""
    if not records:
        console.print("[yellow]No research runs matched the current filters.[/yellow]")
        return

    console.print("[bold]Research Runs:[/bold]")
    for record in records:
        completed = record.completed_at.split("T", 1)[0] if record.completed_at else "n/a"
        console.print(
            "  - "
            f"{record.id} [{record.scope}] {completed} workflows={','.join(record.workflow_ids)}"
        )
        if record.collection:
            console.print(f"      collection: {record.collection}")
        console.print(f"      query: {record.query}")
        if record.bundle_saved_path:
            console.print(f"      bundle: {record.bundle_saved_path}")


def emit_research_timeline(records: list[ResearchTimelineRecord]) -> None:
    """Render a unified project timeline across runs and artifacts."""
    if not records:
        console.print("[yellow]No research timeline events matched the current filters.[/yellow]")
        return

    console.print("[bold]Research Timeline:[/bold]")
    for record in records:
        event_date = record.timestamp.split("T", 1)[0] if record.timestamp else "n/a"
        console.print(
            "  - "
            f"{event_date} ({record.kind}) {record.title}"
        )
        if record.collection:
            console.print(f"      collection: {record.collection}")
        if record.workflow_ids:
            console.print(f"      workflows: {', '.join(record.workflow_ids)}")
        if record.query:
            console.print(f"      query: {record.query}")
        if record.scope:
            console.print(f"      scope: {record.scope}")
        console.print(f"      path: {record.path}")
