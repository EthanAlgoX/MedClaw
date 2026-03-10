"""CLI entry point for MedClaw."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from medclaw import __version__
from medclaw.agent.loop import AgentLoop
from medclaw.application.use_cases import MedicalResearchUseCases
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


def _get_configured_provider():
    """Create the configured provider or exit with a readable message."""
    config = load_config()
    try:
        return config, get_provider(config)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("Run 'medclaw onboard' to set up your configuration")
        raise typer.Exit(1)


async def _run_research_workflow(workflow_id: str, query: str) -> str:
    """Run a typed research workflow."""
    use_cases = _get_research_use_cases()
    _, provider = _get_configured_provider()
    return await use_cases.run_workflow(
        workflow_id=workflow_id,
        query=query,
        provider=provider,
    )


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


@research_app.command("literature-review")
def research_literature_review(query: str):
    """Run the literature review workflow."""
    response = asyncio.run(_run_research_workflow("literature_review", query))
    console.print(Markdown(response))


@research_app.command("clinical-trial-landscape")
def research_clinical_trial_landscape(query: str):
    """Run the clinical trial landscape workflow."""
    response = asyncio.run(_run_research_workflow("clinical_trial_landscape", query))
    console.print(Markdown(response))


@research_app.command("drug-target-landscape")
def research_drug_target_landscape(query: str):
    """Run the drug/target landscape workflow."""
    response = asyncio.run(_run_research_workflow("drug_target_landscape", query))
    console.print(Markdown(response))


@research_app.command("study-design")
def research_study_design(query: str):
    """Run the study design workflow."""
    response = asyncio.run(_run_research_workflow("study_design", query))
    console.print(Markdown(response))


@research_app.command("evidence-brief")
def research_evidence_brief(query: str):
    """Run the evidence brief workflow."""
    response = asyncio.run(_run_research_workflow("evidence_brief", query))
    console.print(Markdown(response))


def main():
    """Main entry point."""
    setup_logging(level="INFO")
    app()


if __name__ == "__main__":
    main()
