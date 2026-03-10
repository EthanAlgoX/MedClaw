"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create an isolated MedClaw workspace for tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace
