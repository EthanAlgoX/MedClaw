"""Configuration loader for MedClaw."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from medclaw.config.schema import MedClawConfig


def get_default_config_path() -> Path:
    """Get default config path."""
    return Path.home() / ".medclaw" / "config.json"


def get_workspace_path() -> Path:
    """Get workspace path."""
    return Path.home() / ".medclaw" / "workspace"


def load_config(config_path: Path | None = None) -> MedClawConfig:
    """Load configuration from file."""
    config_path = config_path or get_default_config_path()

    if not config_path.exists():
        return MedClawConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return MedClawConfig(**data)
    except Exception:
        return MedClawConfig()


def save_config(config: MedClawConfig, config_path: Path | None = None) -> None:
    """Save configuration to file."""
    config_path = config_path or get_default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(mode="json", exclude_none=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_workspace(workspace_path: Path | None = None) -> Path:
    """Ensure workspace directory exists."""
    workspace_path = workspace_path or get_workspace_path()
    workspace_path.mkdir(parents=True, exist_ok=True)

    (workspace_path / "skills").mkdir(exist_ok=True)
    (workspace_path / "memory").mkdir(exist_ok=True)
    (workspace_path / "reports").mkdir(exist_ok=True)
    (workspace_path / "research").mkdir(exist_ok=True)
    (workspace_path / "research" / "collections").mkdir(parents=True, exist_ok=True)
    (workspace_path / "research" / "reports").mkdir(parents=True, exist_ok=True)

    return workspace_path
