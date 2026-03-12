"""Shared CLI helpers and runtime wiring."""

from __future__ import annotations

import json
import sys
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
    build_collection_response,
    build_config_response,
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
    )


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
    latest = record.latest_generated_at.split("T", 1)[0] if record.latest_generated_at else "n/a"
    console.print(f"[bold]{record.collection}[/bold]")
    console.print(f"slug: {record.slug}")
    console.print(f"reports: {record.report_count}")
    console.print(f"latest: {latest}")
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
    if record.workflows:
        console.print(f"active workflows: {', '.join(record.workflows)}")
    if record.latest_bundle_markdown_path:
        console.print(f"latest bundle: {record.latest_bundle_markdown_path}")


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
