"""Root CLI commands."""

from __future__ import annotations

import asyncio

import typer
from rich.panel import Panel

from medclaw import __version__
from medclaw.agent.loop import AgentLoop
from medclaw.application import build_skill_list_response
from medclaw.config.loader import ensure_workspace, get_default_config_path, get_workspace_path, load_config, save_config
from medclaw.config.schema import (
    AgentDefaultsConfig,
    AgentsConfig,
    MedClawConfig,
    ProviderConfig,
    ProvidersConfig,
)
from medclaw.interfaces.cli.common import console, get_provider, write_json


def register_root_commands(app: typer.Typer) -> None:
    """Register top-level CLI commands on the root Typer app."""

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
                write_json(build_skill_list_response(results, query=search))
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
                write_json(build_skill_list_response(all_skills))
                return
            console.print(f"[bold]Available Skills ({len(all_skills)}):[/bold]")
            for s in all_skills:
                console.print(f"  - {s.name} ({s.source})")
