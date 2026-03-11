"""CLI entry point for MedClaw."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from medclaw import __version__
from medclaw.agent.loop import AgentLoop
from medclaw.application.use_cases import MedicalResearchUseCases
from medclaw.evidence.models import ResearchReport
from medclaw.evidence.store import EvidenceStore
from medclaw.config.loader import (
    ensure_workspace,
    get_default_config_path,
    get_workspace_path,
    load_config,
    save_config,
)
from medclaw.providers.deepseek import DeepSeekProvider
from medclaw.providers.openrouter import OpenRouterProvider
from medclaw.utils.logging import setup_logging

app = typer.Typer(help="MedClaw - AI-powered medical research assistant")
research_app = typer.Typer(help="Typed medical research workflows")
console = Console()

app.add_typer(research_app, name="research")


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
        _write_json(report.model_dump(mode="json"))
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
        _write_json([report.model_dump(mode="json") for report in reports])
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
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


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


def _emit_collection_manifest(record: dict) -> None:
    """Render a collection manifest with aggregate report stats."""
    latest = record["latest_generated_at"].split("T", 1)[0] if record["latest_generated_at"] else "n/a"
    console.print(f"[bold]{record['collection']}[/bold]")
    console.print(f"slug: {record['slug']}")
    console.print(f"reports: {record['report_count']}")
    console.print(f"latest: {latest}")
    if record["owner"]:
        console.print(f"owner: {record['owner']}")
    if record["disease_area"]:
        console.print(f"disease area: {record['disease_area']}")
    if record["objective"]:
        console.print(f"objective: {record['objective']}")
    if record["tags"]:
        console.print(f"tags: {', '.join(record['tags'])}")
    if record["preferred_workflows"]:
        console.print(f"preferred workflows: {', '.join(record['preferred_workflows'])}")
    if record["workflows"]:
        console.print(f"active workflows: {', '.join(record['workflows'])}")
    if record.get("latest_bundle_markdown_path"):
        console.print(f"latest bundle: {record['latest_bundle_markdown_path']}")


@app.command()
def skills(search: str | None = None):
    """List available skills."""
    workspace = get_workspace_path()
    from medclaw.agent.skills import SkillsLoader

    loader = SkillsLoader(workspace)

    if search:
        results = loader.search_local_skills(search)
        console.print(f"[bold]Search results for '{search}':[/bold]")
        for r in results:
            description = r.get("description", "")
            source = r.get("source", "unknown")
            reasons = r.get("reasons", "")
            score = r.get("relevance_score")
            suffix = f" [{source}]"
            if score:
                suffix += f" score={score}"
            console.print(f"  - {r['name']}{suffix}: {description}")
            if reasons:
                console.print(f"      reasons: {reasons}")
    else:
        all_skills = loader.list_skills(filter_unavailable=False)
        console.print(f"[bold]Available Skills ({len(all_skills)}):[/bold]")
        for s in all_skills:
            console.print(f"  - {s['name']} ({s['source']})")


@research_app.command("workflows")
def research_workflows():
    """List available typed research workflows."""
    use_cases = _get_research_use_cases()
    workflows = use_cases.list_workflows()
    console.print("[bold]Research Workflows:[/bold]")
    for workflow in workflows:
        console.print(f"  - {workflow['id']}: {workflow['title']}")


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
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of records."),
):
    """List saved research reports and collection bundles."""
    store = _get_evidence_store()
    try:
        records = store.list_artifact_records(
            query=search,
            kind=kind,
            workflow_id=workflow,
            collection=collection,
            since=since,
            until=until,
            limit=limit,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if as_json:
        _write_json(records)
        return

    if not records:
        console.print("[yellow]No research artifacts matched the current filters.[/yellow]")
        return

    filter_suffix = []
    if kind:
        filter_suffix.append(f"kind={kind}")
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
    for record in records:
        generated_at = record["generated_at"].split("T", 1)[0]
        if record["kind"] == "collection_bundle":
            console.print(
                "  - "
                f"{record['id']} [bundle] "
                f"date={generated_at} reports={record['report_count']} "
                f"evidence={record['evidence_count']} citations={record['citation_count']}"
            )
            if record["collection"]:
                console.print(f"      collection: {record['collection']}")
            console.print(f"      title: {record['title']}")
            console.print(f"      workflows: {', '.join(record['workflow_ids'])}")
            if record["summary_preview"]:
                console.print(f"      summary: {record['summary_preview']}")
            continue

        console.print(
            "  - "
            f"{record['filename']} [{record['workflow_id']}] "
            f"date={generated_at} evidence={record['evidence_count']} citations={record['citation_count']}"
        )
        if record["collection"]:
            console.print(f"      collection: {record['collection']}")
        console.print(f"      title: {record['title']}")
        console.print(f"      question: {record['question']}")
        if record["summary_preview"]:
            console.print(f"      summary: {record['summary_preview']}")


@research_app.command("collections")
def research_collections(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of collections."),
):
    """List named research collections."""
    store = _get_evidence_store()
    records = store.list_collection_records(limit=limit)
    if as_json:
        _write_json(records)
        return

    if not records:
        console.print("[yellow]No named research collections found.[/yellow]")
        return

    console.print("[bold]Research Collections:[/bold]")
    for record in records:
        latest = record["latest_generated_at"].split("T", 1)[0] if record["latest_generated_at"] else "n/a"
        console.print(
            "  - "
            f"{record['collection']} reports={record['report_count']} "
            f"evidence={record['evidence_count']} citations={record['citation_count']} latest={latest}"
        )
        if record["owner"]:
            console.print(f"      owner: {record['owner']}")
        if record["disease_area"]:
            console.print(f"      disease area: {record['disease_area']}")
        console.print(f"      workflows: {', '.join(record['workflows'])}")
        if record["tags"]:
            console.print(f"      tags: {', '.join(record['tags'])}")
        console.print(f"      titles: {', '.join(record['titles'][:3])}")
        if record["latest_bundle_markdown_path"]:
            console.print(f"      latest bundle: {record['latest_bundle_markdown_path']}")


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
        record = store.save_collection_manifest(
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

    if as_json:
        _write_json(record)
        return

    console.print(f"[green]Saved collection:[/green] {record['name']}")
    console.print(f"slug: {record['slug']}")


@research_app.command("collection-show")
def research_collection_show(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show a research collection manifest with aggregate stats."""
    store = _get_evidence_store()
    try:
        manifest = store.load_collection_manifest(name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    collection_records = store.list_collection_records(limit=1000)
    merged = next(
        (
            record
            for record in collection_records
            if record["slug"] == manifest["slug"]
        ),
        {
            "collection": manifest["name"],
            **manifest,
            "report_count": 0,
            "evidence_count": 0,
            "citation_count": 0,
            "latest_generated_at": "",
            "workflows": [],
            "titles": [],
        },
    )

    if as_json:
        _write_json(merged)
        return

    _emit_collection_manifest(merged)


@research_app.command("show")
def research_show(
    report: str,
    artifact: str = typer.Option(
        "report",
        "--artifact",
        help="One of: report, evidence, citations, metadata, bundle-markdown, bundle-json.",
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
    normalized_artifact = artifact.replace("-", "_")
    try:
        payload = store.read_artifact(report, artifact=normalized_artifact)
    except (FileNotFoundError, ValueError) as e:
        if normalized_artifact == "report":
            try:
                payload = store.read_bundle_artifact(report, artifact="bundle_markdown")
                normalized_artifact = "bundle_markdown"
            except (FileNotFoundError, ValueError):
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if normalized_artifact == "bundle_markdown":
        if as_json:
            _write_json({"markdown": payload})
            return
        console.print(Markdown(payload))
        return

    if as_json or normalized_artifact != "report":
        _write_json(payload)
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
