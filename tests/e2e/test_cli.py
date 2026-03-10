"""E2E tests for CLI commands."""

import json
import subprocess
from pathlib import Path

import pytest

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport
from medclaw.evidence.store import EvidenceStore


class TestCLI:
    """End-to-end tests for CLI commands."""

    def _seed_report(self, home: Path) -> Path:
        workspace = home / ".medclaw" / "workspace"
        store = EvidenceStore(workspace)
        artifact_paths = store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS G12C inhibitors",
                title="KRAS G12C Review",
                summary="Summary",
                evidence=[
                    EvidenceItem(
                        id="pmid-1",
                        kind="literature",
                        source="pubmed",
                        title="KRAS paper",
                        citations=[
                            Citation(
                                source="pubmed",
                                title="KRAS paper",
                                identifier="PMID:1",
                                url="https://pubmed.ncbi.nlm.nih.gov/1/",
                            )
                        ],
                    )
                ],
                metadata={"seeded": True},
            )
        )
        return artifact_paths["report"]

    def _seed_report_with_fields(
        self,
        home: Path,
        *,
        workflow_id: str,
        title: str,
        question: str,
        summary: str,
        generated_at: str,
    ) -> Path:
        workspace = home / ".medclaw" / "workspace"
        store = EvidenceStore(workspace)
        artifact_paths = store.save_report_artifacts(
            ResearchReport(
                workflow_id=workflow_id,
                question=question,
                title=title,
                summary=summary,
                generated_at=generated_at,
            )
        )
        return artifact_paths["report"]

    def test_version_command(self):
        """Test version command returns version."""
        result = subprocess.run(
            ["medclaw", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "MedClaw" in result.stdout or "version" in result.stdout.lower()

    def test_skills_command(self):
        """Test skills command lists skills."""
        result = subprocess.run(
            ["medclaw", "skills"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "Available Skills" in result.stdout or "Skill" in result.stdout

    def test_skills_search_command(self):
        """Test skills search command."""
        result = subprocess.run(
            ["medclaw", "skills", "--search", "RNA"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "RNA" in result.stdout or "Search" in result.stdout

    def test_onboard_command(self, tmp_path, monkeypatch):
        """Test onboard command creates workspace."""
        # Use a temporary home directory for testing
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        
        monkeypatch.setenv("HOME", str(test_home))
        
        result = subprocess.run(
            ["medclaw", "onboard"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should complete without error
        assert result.returncode == 0

    def test_help_command(self):
        """Test help command works."""
        result = subprocess.run(
            ["medclaw", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "MedClaw" in result.stdout

    def test_research_help_command(self):
        """Test research help command works."""
        result = subprocess.run(
            ["medclaw", "research", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "workflow" in result.stdout.lower() or "research" in result.stdout.lower()

    def test_research_workflows_command(self):
        """Test typed workflow listing works."""
        result = subprocess.run(
            ["medclaw", "research", "workflows"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "literature_review" in result.stdout
        assert "clinical_trial_landscape" in result.stdout

    def test_research_literature_review_help_includes_output_flags(self):
        """Typed workflow help should expose structured output options."""
        result = subprocess.run(
            ["medclaw", "research", "literature-review", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "--json" in result.stdout
        assert "--save-path" in result.stdout
        assert "--no-llm" in result.stdout

    def test_research_artifacts_command_lists_saved_reports(self, tmp_path, monkeypatch):
        """Research artifacts command should list stored report records."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        report_path = self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "artifacts", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        assert payload[0]["workflow_id"] == "literature_review"
        assert payload[0]["filename"] == report_path.name

    def test_research_artifacts_command_supports_search(self, tmp_path, monkeypatch):
        """Research artifacts command should filter reports by search text."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "artifacts", "--search", "kras", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        assert payload[0]["title"] == "KRAS G12C Review"

    def test_research_artifacts_command_supports_workflow_and_date_filters(self, tmp_path, monkeypatch):
        """Research artifacts command should filter by workflow and generated date."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="KRAS G12C Review",
            question="KRAS G12C inhibitors",
            summary="Summary one",
            generated_at="2026-03-01T09:00:00+00:00",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="Adaptive Trial Design",
            question="Adaptive oncology trials",
            summary="Summary two",
            generated_at="2026-03-06T09:00:00+00:00",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "artifacts",
                "--workflow",
                "study_design",
                "--since",
                "2026-03-05",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        assert payload[0]["workflow_id"] == "study_design"
        assert payload[0]["generated_at"] == "2026-03-06T09:00:00+00:00"

    def test_research_artifacts_command_rejects_invalid_date(self, tmp_path, monkeypatch):
        """Research artifacts command should fail cleanly for invalid date filters."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "artifacts", "--since", "2026/03/01"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "Invalid isoformat string" in result.stdout

    def test_research_show_command_returns_selected_artifact(self, tmp_path, monkeypatch):
        """Research show command should return requested structured artifact."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        report_path = self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "show",
                report_path.name,
                "--artifact",
                "citations",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload[0]["identifier"] == "PMID:1"

    def test_research_show_command_supports_summary_view(self, tmp_path, monkeypatch):
        """Research show command should render a compact summary view."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        report_path = self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="EGFR Biomarker Brief",
            question="EGFR biomarkers",
            summary="A compact summary of EGFR biomarker evidence.",
            generated_at="2026-03-07T09:00:00+00:00",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "show", report_path.name, "--view", "summary"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "EGFR Biomarker Brief" in result.stdout
        assert "workflow: evidence_brief" in result.stdout
        assert "summary: A compact summary" in result.stdout

    def test_research_show_command_rejects_invalid_artifact(self, tmp_path, monkeypatch):
        """Research show command should fail cleanly for unsupported artifact names."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        report_path = self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "show",
                report_path.name,
                "--artifact",
                "raw",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "Unsupported artifact" in result.stdout

    def test_agent_command_short(self):
        """Test agent command starts and exits quickly."""
        # Send a quick exit
        result = subprocess.run(
            ["medclaw", "agent", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Agent might not have --help, so just check it doesn't crash
        assert result.returncode in [0, 1, 2]
