"""CLI entry point for MedClaw."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from medclaw import __version__
from medclaw.agent.loop import AgentLoop
from medclaw.application import (
    MedicalResearchUseCases,
    build_artifact_list_response,
    build_artifact_payload_list_response,
    build_artifact_payload_response,
    build_artifact_query_filters,
    build_collection_list_response,
    build_collection_response,
    build_config_response,
    build_provider_list_response,
    build_provider_response,
    build_provider_summary,
    build_research_report_list_response,
    build_research_report_response,
    build_skill_list_response,
    build_workspace_response,
    build_workspace_summary,
    build_workflow_list_response,
)
from medclaw.evidence.api_models import ArtifactRecord, CollectionBundleArtifactRecord, CollectionRecord
from medclaw.evidence.artifacts import (
    CLI_ARTIFACTS,
    CLI_ARTIFACT_HELP,
    artifact_choices_for_kind,
    build_unsupported_artifact_error,
    normalize_artifact_name,
)
from medclaw.evidence.models import ResearchReport
from medclaw.evidence.store import EvidenceStore
from medclaw.config.loader import (
    ensure_workspace,
    get_default_config_path,
    get_workspace_path,
    load_config,
    save_config,
)
from medclaw.config.schema import ProviderConfig
from medclaw.providers.deepseek import DeepSeekProvider
from medclaw.providers.openrouter import OpenRouterProvider
from medclaw.utils.logging import setup_logging

app = typer.Typer(help="MedClaw - AI-powered medical research assistant")
research_app = typer.Typer(help="Typed medical research workflows")
system_app = typer.Typer(help="System inspection and configuration")
console = Console()

app.add_typer(research_app, name="research")
app.add_typer(system_app, name="system")


def get_provider(config):
    """Get the LLM provider based on configuration."""
    provider_name = config.agents.defaults.provider

    if provider_name == "deepseek":
        provider_config = config.providers.deepseek
        if provider_config and provider_config.apiKey:
            return DeepSeekProvider(api_key=provider_config.apiKey)

    if provider_name == "openrouter":
        provider_config = config.providers.openrouter
        if provider_config and provider_config.apiKey:
            return OpenRouterProvider(api_key=provider_config.apiKey)

    raise ValueError(f"Provider {provider_name} not configured or not available")


@app.command()
def version():
    """Show MedClaw version."""
    console.print(f"MedClaw version: {__version__}")


@app.command()
def onboard():
    """Initialize MedClaw workspace and configuration."""
    console.print(Panel.fit(
        "[bold green]Welcome to MedClaw![/bold green]\n"
        "Setting up your medical research assistant...",
        title="MedClaw Setup"
    ))

    workspace = ensure_workspace()
    console.print(f"[green]✓[/green] Workspace created at: {workspace}")

    config_path = get_default_config_path()
    if config_path.exists():
        console.print(f"[yellow]![/yellow] Config already exists at: {config_path}")
    else:
        from medclaw.config.schema import (
            MedClawConfig,
            AgentsConfig,
            AgentDefaultsConfig,
            ProvidersConfig,
            ProviderConfig,
        )
        from medclaw.config.loader import save_config

        default_config = MedClawConfig(
            providers=ProvidersConfig(
                openrouter=ProviderConfig(apiKey="your-api-key-here")
            ),
            agents=AgentsConfig(
                defaults=AgentDefaultsConfig(
                    provider="openrouter",
                    model="anthropic/claude-sonnet-4-20250514"
                )
            )
        )
        save_config(default_config, config_path)
        console.print(f"[green]✓[/green] Config created at: {config_path}")
        console.print("[yellow]![/yellow] Please add your API key to the config file")

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run 'medclaw agent' to start chatting")


@app.command()
def agent(
    model: str | None = None,
    temperature: float = 0.1,
):
    """Start an interactive agent session."""
    config = load_config()

    try:
        provider = get_provider(config)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("Run 'medclaw onboard' to set up your configuration")
        raise typer.Exit(1)

    workspace = get_workspace_path()

    agent_loop = AgentLoop(
        provider=provider,
        workspace=workspace,
        model=model or config.agents.defaults.model,
        temperature=temperature,
    )

    console.print(Panel.fit(
        "[bold]MedClaw Agent[/bold]\n"
        "Type 'exit' or 'quit' to end the session\n"
        "Type 'skills' to see available skills",
        title="MedClaw"
    ))

    history = []

    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ")
            if user_input.lower() in ["exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "skills":
                skills_summary = agent_loop.get_skills_summary()
                console.print(skills_summary)
                continue

            if not user_input.strip():
                continue

            response = asyncio.run(agent_loop.run(user_input, history))
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})

            console.print(f"\n[bold green]MedClaw:[/bold green] {response}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


@system_app.command("workspace")
def system_workspace(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show workspace paths and layout."""
    workspace_summary = _build_workspace_summary()
    if as_json:
        _write_json(build_workspace_response(workspace_summary))
        return

    console.print("[bold]Workspace:[/bold]")
    console.print(f"path: {workspace_summary.path}")
    console.print(f"exists: {workspace_summary.exists}")
    console.print(f"skills: {workspace_summary.skills_path}")
    console.print(f"memory: {workspace_summary.memory_path}")
    console.print(f"reports: {workspace_summary.reports_path}")
    console.print(f"research: {workspace_summary.research_path}")
    console.print(f"collections: {workspace_summary.collections_path}")


@system_app.command("providers")
def system_providers(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show configured providers and default selection."""
    config = load_config()
    providers = _build_provider_summaries(config)
    if as_json:
        _write_json(build_provider_list_response(providers, default_provider=config.agents.defaults.provider))
        return

    console.print("[bold]Providers:[/bold]")
    for provider in providers:
        status = "configured" if provider.configured else "not-configured"
        suffix = " default" if provider.is_default else ""
        console.print(f"  - {provider.name}: {status}{suffix}")
        console.print(f"      api key: {'set' if provider.has_api_key else 'missing'}")
        if provider.base_url:
            console.print(f"      base url: {provider.base_url}")
        if provider.organization:
            console.print(f"      organization: {provider.organization}")


@system_app.command("config")
def system_config(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show configuration summary."""
    config = load_config()
    workspace_summary = _build_workspace_summary()
    providers = _build_provider_summaries(config)
    response = build_config_response(
        config_path=str(get_default_config_path()),
        workspace=workspace_summary,
        default_provider=config.agents.defaults.provider,
        default_model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.maxTokens,
        providers=providers,
    )
    if as_json:
        _write_json(response)
        return

    console.print("[bold]Config:[/bold]")
    console.print(f"config path: {response.item.config_path}")
    console.print(f"default provider: {response.item.default_provider}")
    console.print(f"default model: {response.item.default_model}")
    console.print(f"temperature: {response.item.temperature}")
    console.print(f"max tokens: {response.item.max_tokens}")
    console.print(f"workspace: {response.item.workspace.path}")


@system_app.command("provider-set")
def system_provider_set(
    name: str,
    api_key: str | None = typer.Option(None, "--api-key", help="Provider API key."),
    base_url: str | None = typer.Option(None, "--base-url", help="Provider base URL."),
    organization: str | None = typer.Option(None, "--organization", help="Provider organization."),
    make_default: bool = typer.Option(False, "--default", help="Make this the default provider."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Create or update one provider configuration."""
    if name not in {"openai", "anthropic", "openrouter", "deepseek", "google"}:
        console.print("[red]Error:[/red] Unsupported provider. Choose from: openai, anthropic, openrouter, deepseek, google")
        raise typer.Exit(1)

    config = load_config()
    current = getattr(config.providers, name, None) or ProviderConfig()
    updated = ProviderConfig(
        apiKey=api_key if api_key is not None else current.apiKey,
        baseUrl=base_url if base_url is not None else current.baseUrl,
        organization=organization if organization is not None else current.organization,
    )
    setattr(config.providers, name, updated)
    if make_default:
        config.agents.defaults.provider = name
    save_config(config)

    provider = build_provider_summary(
        name=name,
        configured=True,
        has_api_key=bool(updated.apiKey),
        base_url=updated.baseUrl,
        organization=updated.organization,
        is_default=config.agents.defaults.provider == name,
    )
    if as_json:
        _write_json(build_provider_response(provider))
        return

    console.print(f"[green]Updated provider:[/green] {provider.name}")
    console.print(f"default: {provider.is_default}")
    console.print(f"api key: {'set' if provider.has_api_key else 'missing'}")
    if provider.base_url:
        console.print(f"base url: {provider.base_url}")
    if provider.organization:
        console.print(f"organization: {provider.organization}")


def _get_research_use_cases() -> MedicalResearchUseCases:
    """Create research use cases for the configured workspace."""
    workspace = get_workspace_path()
    ensure_workspace(workspace)
    return MedicalResearchUseCases(workspace)


def _get_evidence_store() -> EvidenceStore:
    """Create an evidence store for the configured workspace."""
    workspace = get_workspace_path()
    ensure_workspace(workspace)
    return EvidenceStore(workspace)


def _get_configured_provider():
    """Create the configured provider or exit with a readable message."""
    config = load_config()
    try:
        return config, get_provider(config)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("Run 'medclaw onboard' to set up your configuration")
        raise typer.Exit(1)


def _build_provider_summaries(config) -> list:
    """Build typed provider summaries from config."""
    summaries = []
    for name in ("openai", "anthropic", "openrouter", "deepseek", "google"):
        provider = getattr(config.providers, name, None)
        summaries.append(
            build_provider_summary(
                name=name,
                configured=provider is not None,
                has_api_key=bool(provider and provider.apiKey),
                base_url=provider.baseUrl if provider else None,
                organization=provider.organization if provider else None,
                is_default=config.agents.defaults.provider == name,
            )
        )
    return summaries


def _build_workspace_summary() -> object:
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


async def _run_research_workflow_report(
    workflow_id: str,
    query: str,
    no_llm: bool = False,
    collection: str | None = None,
) -> ResearchReport:
    """Run a typed research workflow with optional LLM synthesis disabled."""
    use_cases = _get_research_use_cases()
    provider = None
    if not no_llm:
        _, provider = _get_configured_provider()
    return await use_cases.run_workflow_report(
        workflow_id=workflow_id,
        query=query,
        provider=provider,
        collection=collection,
    )


def _emit_research_report(
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
        _write_json(build_research_report_response(report))
        return
    from medclaw.reporting.briefs import render_research_report

    console.print(Markdown(render_research_report(report)))


def _emit_research_reports(
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
        _write_json(build_research_report_list_response(reports))
        return

    if len(reports) > 1:
        from medclaw.reporting.briefs import render_collection_report_bundle

        console.print(Markdown(render_collection_report_bundle(reports)))
        bundle_saved_path = reports[0].metadata.get("bundle_saved_path", "")
        if bundle_saved_path:
            console.print(f"\nBundle summary saved to: {bundle_saved_path}")
        return

    _emit_research_report(reports[0])


def _write_json(payload) -> None:
    """Write machine-readable JSON without terminal wrapping."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


def _emit_artifact_record(record: ArtifactRecord, store: EvidenceStore) -> None:
    """Render a single artifact record into user-facing output."""
    if isinstance(record, CollectionBundleArtifactRecord):
        markdown = store.read_bundle_artifact(record.id, artifact="bundle_markdown")
        console.print(Markdown(markdown))
        return

    payload = store.read_artifact(record.id, artifact="report")
    report_model = ResearchReport.model_validate(payload)
    _emit_research_report(report_model)


def _normalize_artifact_option(artifact: str | None) -> str | None:
    """Normalize CLI artifact option names."""
    return normalize_artifact_name(artifact, choices=CLI_ARTIFACTS)


def _artifact_paths_for_record(record: ArtifactRecord, store: EvidenceStore) -> dict[str, Path]:
    """Return the artifact path bundle for a unified artifact record."""
    if isinstance(record, CollectionBundleArtifactRecord):
        return store.get_bundle_artifact_paths(record.id)
    return store.get_artifact_paths(record.id)


def _artifact_payload_for_record(record: ArtifactRecord, store: EvidenceStore, artifact: str):
    """Read a specific artifact payload for a unified artifact record."""
    supported = artifact_choices_for_kind(record.kind)
    if artifact not in supported:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    if isinstance(record, CollectionBundleArtifactRecord):
        return store.read_bundle_artifact(record.id, artifact=artifact)
    return store.read_artifact(record.id, artifact=artifact)


def _artifact_path_for_record(record: ArtifactRecord, store: EvidenceStore, artifact: str) -> str:
    """Resolve a specific artifact path for a unified artifact record."""
    supported = artifact_choices_for_kind(record.kind)
    if artifact not in supported:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    paths = _artifact_paths_for_record(record, store)
    if artifact not in paths:
        raise build_unsupported_artifact_error(artifact.replace("_", "-"), supported, kind=record.kind)
    return str(paths[artifact])


def _artifact_primary_path(record: ArtifactRecord) -> str:
    """Return the primary file path for an artifact record."""
    if isinstance(record, CollectionBundleArtifactRecord):
        return record.bundle_markdown_path
    return record.path


def _read_show_artifact(store: EvidenceStore, target: str, artifact: str) -> tuple[str, object]:
    """Read a report or bundle artifact for the show command."""
    normalized_artifact = _normalize_artifact_option(artifact) or "report"
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


def _write_lines(lines: list[str]) -> None:
    """Write plain lines without terminal wrapping."""
    for line in lines:
        sys.stdout.write(line)
        sys.stdout.write("\n")


def _emit_artifact_record_list(records: list[ArtifactRecord]) -> None:
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


def _emit_report_summary(report: ResearchReport) -> None:
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


def _emit_collection_manifest(record: CollectionRecord) -> None:
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


@app.command()
def skills(
    search: str | None = None,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """List available skills."""
    workspace = get_workspace_path()
    from medclaw.agent.skills import SkillsLoader

    loader = SkillsLoader(workspace)

    if search:
        results = loader.search_local_skill_models(search)
        if as_json:
            _write_json(build_skill_list_response(results, query=search))
            return
        console.print(f"[bold]Search results for '{search}':[/bold]")
        for r in results:
            suffix = f" [{r.source}]"
            if r.relevance_score:
                suffix += f" score={r.relevance_score}"
            console.print(f"  - {r.name}{suffix}: {r.description}")
            if r.reasons:
                console.print(f"      reasons: {r.reasons}")
    else:
        all_skills = loader.list_skill_models(filter_unavailable=False)
        if as_json:
            _write_json(build_skill_list_response(all_skills))
            return
        console.print(f"[bold]Available Skills ({len(all_skills)}):[/bold]")
        for s in all_skills:
            console.print(f"  - {s.name} ({s.source})")


@research_app.command("workflows")
def research_workflows(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """List available typed research workflows."""
    use_cases = _get_research_use_cases()
    workflows = use_cases.list_workflow_models()
    if as_json:
        _write_json(build_workflow_list_response(workflows))
        return
    console.print("[bold]Research Workflows:[/bold]")
    for workflow in workflows:
        console.print(f"  - {workflow.id}: {workflow.title}")


@research_app.command("run")
def research_run(
    query: str,
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Use collection preferences and metadata for workflow selection.",
    ),
    workflow: str | None = typer.Option(
        None,
        "--workflow",
        help="Explicit workflow id to run instead of collection preference.",
    ),
    all_preferred: bool = typer.Option(
        False,
        "--all-preferred",
        help="Run every preferred workflow defined on the collection.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only saved report paths."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run collection-aware research workflows."""
    use_cases = _get_research_use_cases()
    provider = None
    if not no_llm:
        _, provider = _get_configured_provider()

    reports = asyncio.run(
        use_cases.run_collection_reports(
            query=query,
            provider=provider,
            collection=collection,
            workflow_id=workflow,
            all_preferred=all_preferred,
            persist_bundle=True,
        )
    )
    _emit_research_reports(reports, as_json=as_json, save_path_only=save_path)


@research_app.command("artifacts")
def research_artifacts(
    search: str | None = typer.Option(None, "--search", help="Filter saved reports by text."),
    kind: str | None = typer.Option(None, "--kind", help="Artifact kind: report or bundle."),
    workflow: str | None = typer.Option(None, "--workflow", help="Filter by workflow id."),
    collection: str | None = typer.Option(None, "--collection", help="Filter by collection name."),
    since: str | None = typer.Option(None, "--since", help="Only include reports on/after YYYY-MM-DD."),
    until: str | None = typer.Option(None, "--until", help="Only include reports on/before YYYY-MM-DD."),
    latest: bool = typer.Option(False, "--latest", help="Return only the newest matching artifact."),
    latest_by_collection: bool = typer.Option(
        False,
        "--latest-by-collection",
        help="Return the newest matching artifact for each named collection.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of records."),
):
    """List saved research reports and collection bundles."""
    store = _get_evidence_store()
    filters = build_artifact_query_filters(
        query=search,
        kind=kind,
        workflow_id=workflow,
        collection=collection,
        since=since,
        until=until,
        latest=latest,
        latest_by_collection=latest_by_collection,
        limit=limit,
    )
    try:
        records = store.list_artifact_records(
            query=search,
            kind=kind,
            workflow_id=workflow,
            collection=collection,
            since=since,
            until=until,
            latest=latest,
            latest_by_collection=latest_by_collection,
            limit=limit,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    typed_records = store.list_artifact_record_models(
        query=search,
        kind=kind,
        workflow_id=workflow,
        collection=collection,
        since=since,
        until=until,
        latest=latest,
        latest_by_collection=latest_by_collection,
        limit=limit,
    )

    if as_json:
        _write_json(build_artifact_list_response(typed_records, filters))
        return

    if not typed_records:
        console.print("[yellow]No research artifacts matched the current filters.[/yellow]")
        return

    filter_suffix = []
    if kind:
        filter_suffix.append(f"kind={kind}")
    if latest:
        filter_suffix.append("latest")
    if latest_by_collection:
        filter_suffix.append("latest_by_collection")
    if workflow:
        filter_suffix.append(f"workflow={workflow}")
    if collection:
        filter_suffix.append(f"collection={collection}")
    if since:
        filter_suffix.append(f"since={since}")
    if until:
        filter_suffix.append(f"until={until}")
    if search:
        filter_suffix.append(f"search={search}")
    suffix = f" ({', '.join(filter_suffix)})" if filter_suffix else ""

    console.print(f"[bold]Research Artifacts{suffix}:[/bold]")
    for record in typed_records:
        generated_at = record.generated_at.split("T", 1)[0]
        if isinstance(record, CollectionBundleArtifactRecord):
            console.print(
                "  - "
                f"{record.id} [bundle] "
                f"date={generated_at} reports={record.report_count} "
                f"evidence={record.evidence_count} citations={record.citation_count}"
            )
            if record.collection:
                console.print(f"      collection: {record.collection}")
            console.print(f"      title: {record.title}")
            console.print(f"      workflows: {', '.join(record.workflow_ids)}")
            if record.summary_preview:
                console.print(f"      summary: {record.summary_preview}")
            continue

        console.print(
            "  - "
            f"{record.filename} [{record.workflow_id}] "
            f"date={generated_at} evidence={record.evidence_count} citations={record.citation_count}"
        )
        if record.collection:
            console.print(f"      collection: {record.collection}")
        console.print(f"      title: {record.title}")
        console.print(f"      question: {record.question}")
        if record.summary_preview:
            console.print(f"      summary: {record.summary_preview}")


@research_app.command("latest")
def research_latest(
    kind: str | None = typer.Option(None, "--kind", help="Artifact kind: report or bundle."),
    artifact: str | None = typer.Option(
        None,
        "--artifact",
        help=CLI_ARTIFACT_HELP,
    ),
    workflow: str | None = typer.Option(None, "--workflow", help="Filter by workflow id."),
    collection: str | None = typer.Option(None, "--collection", help="Filter by collection name."),
    by_collection: bool = typer.Option(
        False,
        "--by-collection",
        help="Return the newest artifact for each named collection.",
    ),
    show: bool = typer.Option(
        False,
        "--show",
        help="With --by-collection, render each artifact instead of listing summaries.",
    ),
    save_path: bool = typer.Option(
        False,
        "--save-path",
        help="Print the primary artifact path instead of rendering content.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show the latest saved research artifact."""
    store = _get_evidence_store()
    filters = build_artifact_query_filters(
        kind=kind,
        workflow_id=workflow,
        collection=collection,
        latest=not by_collection,
        latest_by_collection=by_collection,
        limit=50 if by_collection else 1,
    )
    try:
        normalized_artifact = _normalize_artifact_option(artifact)
        records = store.list_artifact_records(
            kind=kind,
            workflow_id=workflow,
            collection=collection,
            latest=not by_collection,
            latest_by_collection=by_collection,
            limit=50 if by_collection else 1,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    typed_records = store.list_artifact_record_models(
        kind=kind,
        workflow_id=workflow,
        collection=collection,
        latest=not by_collection,
        latest_by_collection=by_collection,
        limit=50 if by_collection else 1,
    )

    if not typed_records:
        console.print("[yellow]No research artifacts matched the current filters.[/yellow]")
        return

    if save_path:
        try:
            paths = [
                _artifact_path_for_record(record, store, normalized_artifact)
                if normalized_artifact
                else _artifact_primary_path(record)
                for record in typed_records
            ]
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        _write_lines(paths)
        return

    if normalized_artifact:
        try:
            payloads = [
                _artifact_payload_for_record(record, store, normalized_artifact)
                for record in typed_records
            ]
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        if as_json:
            items = [
                build_artifact_payload_response(
                    target=record.id,
                    artifact=normalized_artifact,
                    record=record,
                    path=_artifact_path_for_record(record, store, normalized_artifact),
                    payload=payload,
                )
                for record, payload in zip(typed_records, payloads, strict=True)
            ]
            _write_json(build_artifact_payload_list_response(items, filters=filters))
            return

        for index, payload in enumerate(payloads):
            if index:
                console.print("\n---\n")
            if normalized_artifact == "bundle_markdown":
                console.print(Markdown(payload))
            elif normalized_artifact == "report":
                report_model = ResearchReport.model_validate(payload)
                _emit_research_report(report_model)
            else:
                _write_json(payload)
        return

    if as_json:
        _write_json(build_artifact_list_response(typed_records, filters))
        return

    if by_collection and not show:
        _emit_artifact_record_list(typed_records)
        return

    for index, record in enumerate(typed_records):
        if index:
            console.print("\n---\n")
        _emit_artifact_record(record, store)


@research_app.command("collections")
def research_collections(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of collections."),
):
    """List named research collections."""
    store = _get_evidence_store()
    records = store.list_collection_record_models(limit=limit)
    if as_json:
        _write_json(build_collection_list_response(records, limit=limit))
        return

    if not records:
        console.print("[yellow]No named research collections found.[/yellow]")
        return

    console.print("[bold]Research Collections:[/bold]")
    for record in records:
        latest = record.latest_generated_at.split("T", 1)[0] if record.latest_generated_at else "n/a"
        console.print(
            "  - "
            f"{record.collection} reports={record.report_count} "
            f"evidence={record.evidence_count} citations={record.citation_count} latest={latest}"
        )
        if record.owner:
            console.print(f"      owner: {record.owner}")
        if record.disease_area:
            console.print(f"      disease area: {record.disease_area}")
        console.print(f"      workflows: {', '.join(record.workflows)}")
        if record.tags:
            console.print(f"      tags: {', '.join(record.tags)}")
        console.print(f"      titles: {', '.join(record.titles[:3])}")
        if record.latest_bundle_markdown_path:
            console.print(f"      latest bundle: {record.latest_bundle_markdown_path}")


@research_app.command("collection-set")
def research_collection_set(
    name: str,
    objective: str = typer.Option("", "--objective", help="Research objective for this collection."),
    disease_area: str = typer.Option("", "--disease-area", help="Disease area or focus domain."),
    owner: str = typer.Option("", "--owner", help="Collection owner or lead."),
    tags: list[str] | None = typer.Option(None, "--tag", help="Repeatable collection tag."),
    preferred_workflows: list[str] | None = typer.Option(
        None,
        "--preferred-workflow",
        help="Repeatable preferred workflow id.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Create or update a research collection manifest."""
    store = _get_evidence_store()
    try:
        store.save_collection_manifest(
            name=name,
            objective=objective,
            disease_area=disease_area,
            owner=owner,
            tags=tags or [],
            preferred_workflows=preferred_workflows or [],
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    saved_manifest = store.load_collection_manifest_model(name)

    if as_json:
        _write_json(build_collection_response(saved_manifest))
        return

    console.print(f"[green]Saved collection:[/green] {saved_manifest.name}")
    console.print(f"slug: {saved_manifest.slug}")


@research_app.command("collection-show")
def research_collection_show(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show a research collection manifest with aggregate stats."""
    store = _get_evidence_store()
    try:
        collection_record = store.get_collection_record_model(name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if as_json:
        _write_json(build_collection_response(collection_record))
        return

    _emit_collection_manifest(collection_record)


@research_app.command("show")
def research_show(
    report: str,
    artifact: str = typer.Option(
        "report",
        "--artifact",
        help=CLI_ARTIFACT_HELP,
    ),
    view: str = typer.Option(
        "full",
        "--view",
        help="For report artifacts: full or summary.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON payload."),
):
    """Show a saved research report or one of its companion artifacts."""
    store = _get_evidence_store()
    try:
        normalized_artifact, payload = _read_show_artifact(store, report, artifact)
        record = store.get_artifact_record_model(report)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if normalized_artifact == "bundle_markdown":
        if as_json:
            _write_json(
                build_artifact_payload_response(
                    target=report,
                    artifact=normalized_artifact,
                    record=record,
                    path=_artifact_path_for_record(record, store, normalized_artifact),
                    payload=payload,
                )
            )
            return
        console.print(Markdown(payload))
        return

    if as_json or normalized_artifact != "report":
        _write_json(
            build_artifact_payload_response(
                target=report,
                artifact=normalized_artifact,
                record=record,
                path=_artifact_path_for_record(record, store, normalized_artifact),
                payload=payload,
            )
        )
        return

    report_model = ResearchReport.model_validate(payload)
    if view == "summary":
        _emit_report_summary(report_model)
        return
    if view != "full":
        console.print("[red]Error:[/red] Unsupported view. Choose from: full, summary")
        raise typer.Exit(1)
    _emit_research_report(report_model)


@research_app.command("literature-review")
def research_literature_review(
    query: str,
    collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run the literature review workflow."""
    report = asyncio.run(
        _run_research_workflow_report(
            "literature_review",
            query,
            no_llm=no_llm,
            collection=collection,
        )
    )
    _emit_research_report(report, as_json=as_json, save_path_only=save_path)


@research_app.command("clinical-trial-landscape")
def research_clinical_trial_landscape(
    query: str,
    collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run the clinical trial landscape workflow."""
    report = asyncio.run(
        _run_research_workflow_report(
            "clinical_trial_landscape",
            query,
            no_llm=no_llm,
            collection=collection,
        )
    )
    _emit_research_report(report, as_json=as_json, save_path_only=save_path)


@research_app.command("drug-target-landscape")
def research_drug_target_landscape(
    query: str,
    collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run the drug/target landscape workflow."""
    report = asyncio.run(
        _run_research_workflow_report(
            "drug_target_landscape",
            query,
            no_llm=no_llm,
            collection=collection,
        )
    )
    _emit_research_report(report, as_json=as_json, save_path_only=save_path)


@research_app.command("study-design")
def research_study_design(
    query: str,
    collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run the study design workflow."""
    report = asyncio.run(
        _run_research_workflow_report(
            "study_design",
            query,
            no_llm=no_llm,
            collection=collection,
        )
    )
    _emit_research_report(report, as_json=as_json, save_path_only=save_path)


@research_app.command("evidence-brief")
def research_evidence_brief(
    query: str,
    collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
):
    """Run the evidence brief workflow."""
    report = asyncio.run(
        _run_research_workflow_report(
            "evidence_brief",
            query,
            no_llm=no_llm,
            collection=collection,
        )
    )
    _emit_research_report(report, as_json=as_json, save_path_only=save_path)


def main():
    """Main entry point."""
    setup_logging(level="INFO")
    app()


if __name__ == "__main__":
    main()
