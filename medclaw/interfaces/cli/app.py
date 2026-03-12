"""CLI bootstrap assembly."""

from __future__ import annotations

import typer

from medclaw.interfaces.cli.research import research_app
from medclaw.interfaces.cli.root import register_root_commands
from medclaw.interfaces.cli.system import system_app


def create_app() -> typer.Typer:
    """Create the MedClaw CLI application."""
    app = typer.Typer(help="MedClaw - AI-powered medical research assistant")
    register_root_commands(app)
    app.add_typer(research_app, name="research")
    app.add_typer(system_app, name="system")
    return app
