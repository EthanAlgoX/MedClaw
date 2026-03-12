"""Research workflow and artifact CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.markdown import Markdown

from medclaw.application import (
    build_artifact_list_response,
    build_artifact_payload_list_response,
    build_artifact_payload_response,
    build_artifact_query_filters,
    build_collection_list_response,
    build_collection_response,
    build_research_run_list_response,
    build_research_run_query_filters,
    build_research_run_response,
    build_workflow_list_response,
)
from medclaw.evidence.api_models import CollectionBundleArtifactRecord
from medclaw.evidence.models import ResearchReport
from medclaw.interfaces.cli.common import (
    CLI_ARTIFACT_HELP,
    artifact_path_for_record,
    artifact_payload_for_record,
    artifact_primary_path,
    console,
    emit_artifact_record,
    emit_artifact_record_list,
    emit_collection_manifest,
    emit_research_run,
    emit_research_run_record_list,
    emit_report_summary,
    emit_research_report,
    emit_research_reports,
    get_configured_provider,
    get_evidence_store,
    get_research_use_cases,
    normalize_artifact_option,
    read_show_artifact,
    run_research_workflow_report,
    write_json,
    write_lines,
)

research_app = typer.Typer(help="Typed medical research workflows")


@research_app.command("workflows")
def research_workflows(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """List available typed research workflows."""
    use_cases = get_research_use_cases()
    workflows = use_cases.list_workflow_models()
    if as_json:
        write_json(build_workflow_list_response(workflows))
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
    use_cases = get_research_use_cases()
    provider = None
    if not no_llm:
        _, provider = get_configured_provider()

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
    emit_research_reports(reports, as_json=as_json, save_path_only=save_path)


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
    store = get_evidence_store()
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
        store.list_artifact_records(
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
        write_json(build_artifact_list_response(typed_records, filters))
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
    store = get_evidence_store()
    filters = build_artifact_query_filters(
        kind=kind,
        workflow_id=workflow,
        collection=collection,
        latest=not by_collection,
        latest_by_collection=by_collection,
        limit=50 if by_collection else 1,
    )
    try:
        normalized_artifact = normalize_artifact_option(artifact)
        typed_records = store.list_artifact_record_models(
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

    if not typed_records:
        console.print("[yellow]No research artifacts matched the current filters.[/yellow]")
        raise typer.Exit(1)

    if save_path:
        try:
            paths = [
                artifact_path_for_record(record, store, normalized_artifact)
                if normalized_artifact
                else artifact_primary_path(record)
                for record in typed_records
            ]
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        write_lines(paths)
        return

    if normalized_artifact:
        try:
            payloads = [
                artifact_payload_for_record(record, store, normalized_artifact)
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
                    path=artifact_path_for_record(record, store, normalized_artifact),
                    payload=payload,
                )
                for record, payload in zip(typed_records, payloads, strict=True)
            ]
            write_json(build_artifact_payload_list_response(items, filters=filters))
            return

        for index, payload in enumerate(payloads):
            if index:
                console.print("\n---\n")
            if normalized_artifact == "bundle_markdown":
                console.print(Markdown(payload))
            elif normalized_artifact == "report":
                report_model = ResearchReport.model_validate(payload)
                emit_research_report(report_model)
            else:
                write_json(payload)
        return

    if as_json:
        write_json(build_artifact_list_response(typed_records, filters))
        return

    if by_collection and not show:
        emit_artifact_record_list(typed_records)
        return

    for index, record in enumerate(typed_records):
        if index:
            console.print("\n---\n")
        emit_artifact_record(record, store)


@research_app.command("collections")
def research_collections(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of collections."),
):
    """List named research collections."""
    store = get_evidence_store()
    records = store.list_collection_record_models(limit=limit)
    if as_json:
        write_json(build_collection_list_response(records, limit=limit))
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
    store = get_evidence_store()
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
        write_json(build_collection_response(saved_manifest))
        return

    console.print(f"[green]Saved collection:[/green] {saved_manifest.name}")
    console.print(f"slug: {saved_manifest.slug}")


@research_app.command("collection-show")
def research_collection_show(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show a research collection manifest with aggregate stats."""
    store = get_evidence_store()
    try:
        collection_record = store.get_collection_record_model(name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if as_json:
        write_json(build_collection_response(collection_record))
        return

    emit_collection_manifest(collection_record)


@research_app.command("runs")
def research_runs(
    search: str | None = typer.Option(None, "--search", help="Filter saved runs by text."),
    workflow: str | None = typer.Option(None, "--workflow", help="Filter by workflow id."),
    collection: str | None = typer.Option(None, "--collection", help="Filter by collection name."),
    latest: bool = typer.Option(False, "--latest", help="Return only the newest matching run."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of runs."),
):
    """List saved research runs."""
    store = get_evidence_store()
    filters = build_research_run_query_filters(
        query=search,
        collection=collection,
        workflow_id=workflow,
        latest=latest,
        limit=limit,
    )
    typed_records = store.list_run_record_models(
        query=search,
        collection=collection,
        workflow_id=workflow,
        latest=latest,
        limit=limit,
    )

    if as_json:
        write_json(build_research_run_list_response(typed_records, filters))
        return

    emit_research_run_record_list(typed_records)


@research_app.command("run-show")
def research_run_show(
    run: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show a saved research run."""
    store = get_evidence_store()
    try:
        run_model = store.load_run(run)
        record = store.get_run_record_model(run)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if as_json:
        write_json(
            build_research_run_response(
                target=run,
                path=str(store.resolve_run_path(run)),
                record=record,
                run=run_model,
            )
        )
        return

    emit_research_run(run_model)


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
    store = get_evidence_store()
    try:
        normalized_artifact, payload = read_show_artifact(store, report, artifact)
        record = store.get_artifact_record_model(report)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if normalized_artifact == "bundle_markdown":
        if as_json:
            write_json(
                build_artifact_payload_response(
                    target=report,
                    artifact=normalized_artifact,
                    record=record,
                    path=artifact_path_for_record(record, store, normalized_artifact),
                    payload=payload,
                )
            )
            return
        console.print(Markdown(payload))
        return

    if as_json or normalized_artifact != "report":
        write_json(
            build_artifact_payload_response(
                target=report,
                artifact=normalized_artifact,
                record=record,
                path=artifact_path_for_record(record, store, normalized_artifact),
                payload=payload,
            )
        )
        return

    report_model = ResearchReport.model_validate(payload)
    if view == "summary":
        emit_report_summary(report_model)
        return
    if view != "full":
        console.print("[red]Error:[/red] Unsupported view. Choose from: full, summary")
        raise typer.Exit(1)
    emit_research_report(report_model)


def _register_workflow_command(
    workflow_id: str,
    command_name: str,
    help_text: str,
):
    """Create one typed workflow CLI command."""

    @research_app.command(command_name)
    def _command(
        query: str,
        collection: str | None = typer.Option(None, "--collection", help="Group this report under a named collection."),
        as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
        save_path: bool = typer.Option(False, "--save-path", help="Print only the saved report path."),
        no_llm: bool = typer.Option(False, "--no-llm", help="Run without model synthesis."),
    ):
        report = asyncio.run(
            run_research_workflow_report(
                workflow_id,
                query,
                no_llm=no_llm,
                collection=collection,
            )
        )
        emit_research_report(report, as_json=as_json, save_path_only=save_path)

    _command.__doc__ = help_text
    return _command


_register_workflow_command("literature_review", "literature-review", "Run the literature review workflow.")
_register_workflow_command("clinical_trial_landscape", "clinical-trial-landscape", "Run the clinical trial landscape workflow.")
_register_workflow_command("drug_target_landscape", "drug-target-landscape", "Run the drug/target landscape workflow.")
_register_workflow_command("study_design", "study-design", "Run the study design workflow.")
_register_workflow_command("evidence_brief", "evidence-brief", "Run the evidence brief workflow.")
