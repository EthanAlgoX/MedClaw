"""CLI entry point for MedClaw."""

from __future__ import annotations

from medclaw.interfaces.cli.app import create_app
from medclaw.utils.logging import setup_logging

app = create_app()


def main():
    """Main entry point."""
    setup_logging(level="INFO")
    app()


if __name__ == "__main__":
    main()
