"""Persistence for research reports and evidence artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from medclaw.evidence.models import ResearchReport


class EvidenceStore:
    """Persist research artifacts to the workspace."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.base_path = workspace / "research"
        self.reports_path = self.base_path / "reports"
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: ResearchReport) -> Path:
        """Save a structured research report to disk."""
        slug = report.workflow_id.replace("/", "-").replace("_", "-")
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{slug}.json"
        path = self.reports_path / filename
        path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def list_reports(self) -> list[Path]:
        """List saved research reports, newest first."""
        return sorted(self.reports_path.glob("*.json"), reverse=True)
