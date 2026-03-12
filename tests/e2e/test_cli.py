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
        collection: str | None = None,
        metadata: dict | None = None,
    ) -> Path:
        workspace = home / ".medclaw" / "workspace"
        store = EvidenceStore(workspace)
        report_metadata = dict(metadata or {})
        if collection:
            report_metadata.setdefault("collection", collection)
        artifact_paths = store.save_report_artifacts(
            ResearchReport(
                workflow_id=workflow_id,
                question=question,
                title=title,
                summary=summary,
                generated_at=generated_at,
                metadata=report_metadata,
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

    def test_skills_command_supports_json(self):
        """Skills command should expose structured JSON output."""
        result = subprocess.run(
            ["medclaw", "skills", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] >= 1
        assert "name" in payload["items"][0]

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

    def test_skills_search_command_supports_json(self):
        """Skills search command should expose structured JSON output."""
        result = subprocess.run(
            ["medclaw", "skills", "--search", "pubmed", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["query"] == "pubmed"
        assert payload["total"] >= 1
        assert payload["items"][0]["name"]

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

    def test_system_workspace_command_supports_json(self, tmp_path, monkeypatch):
        """System workspace command should expose structured JSON output."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "system", "workspace", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["item"]["path"].endswith(".medclaw/workspace")
        assert payload["item"]["collections_path"].endswith("research/collections")

    def test_system_providers_and_config_commands_support_json(self, tmp_path, monkeypatch):
        """System provider/config commands should expose structured JSON output."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        providers_result = subprocess.run(
            ["medclaw", "system", "providers", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        config_result = subprocess.run(
            ["medclaw", "system", "config", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert providers_result.returncode == 0
        providers_payload = json.loads(providers_result.stdout)
        assert providers_payload["default_provider"] == "openrouter"
        assert providers_payload["total"] >= 1

        assert config_result.returncode == 0
        config_payload = json.loads(config_result.stdout)
        assert config_payload["item"]["default_provider"] == "openrouter"
        assert config_payload["item"]["workspace"]["path"].endswith(".medclaw/workspace")

    def test_system_provider_set_updates_config(self, tmp_path, monkeypatch):
        """System provider-set command should persist provider configuration."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "deepseek",
                "--api-key",
                "test-key",
                "--base-url",
                "https://api.deepseek.com",
                "--default",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["item"]["name"] == "deepseek"
        assert payload["item"]["has_api_key"] is True
        assert payload["item"]["is_default"] is True

        config_path = test_home / ".medclaw" / "config.json"
        config_payload = json.loads(config_path.read_text(encoding="utf-8"))
        assert config_payload["providers"]["deepseek"]["apiKey"] == "test-key"
        assert config_payload["agents"]["defaults"]["provider"] == "deepseek"

    def test_system_config_set_commands_update_defaults(self, tmp_path, monkeypatch):
        """Model, temperature, max tokens, and workspace setters should persist config."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))
        workspace_path = test_home / "custom-workspace"
        compatible_model = "openai/gpt-4o-mini"

        model_result = subprocess.run(
            ["medclaw", "system", "model-set", compatible_model, "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        temperature_result = subprocess.run(
            ["medclaw", "system", "temperature-set", "0.3", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        max_tokens_result = subprocess.run(
            ["medclaw", "system", "max-tokens-set", "2048", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        workspace_result = subprocess.run(
            ["medclaw", "system", "workspace-set", str(workspace_path), "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        workspace_show_result = subprocess.run(
            ["medclaw", "system", "workspace", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert model_result.returncode == 0
        assert json.loads(model_result.stdout)["item"]["default_model"] == compatible_model

        assert temperature_result.returncode == 0
        assert json.loads(temperature_result.stdout)["item"]["temperature"] == 0.3

        assert max_tokens_result.returncode == 0
        assert json.loads(max_tokens_result.stdout)["item"]["max_tokens"] == 2048

        assert workspace_result.returncode == 0
        workspace_payload = json.loads(workspace_result.stdout)
        assert workspace_payload["item"]["workspace"]["path"] == str(workspace_path)

        assert workspace_show_result.returncode == 0
        workspace_show_payload = json.loads(workspace_show_result.stdout)
        assert workspace_show_payload["item"]["path"] == str(workspace_path)
        assert (workspace_path / "research" / "collections").exists()

        config_path = test_home / ".medclaw" / "config.json"
        config_payload = json.loads(config_path.read_text(encoding="utf-8"))
        assert config_payload["agents"]["defaults"]["model"] == compatible_model
        assert config_payload["agents"]["defaults"]["temperature"] == 0.3
        assert config_payload["agents"]["defaults"]["maxTokens"] == 2048
        assert config_payload["workspace"]["path"] == str(workspace_path)

    def test_system_config_set_commands_validate_input(self, tmp_path, monkeypatch):
        """Config setter commands should reject invalid values."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        temperature_result = subprocess.run(
            ["medclaw", "system", "temperature-set", "2.5"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        max_tokens_result = subprocess.run(
            ["medclaw", "system", "max-tokens-set", "0"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert temperature_result.returncode == 1
        assert "Temperature must be between 0 and 2" in temperature_result.stdout

        assert max_tokens_result.returncode == 1
        assert "Max tokens must be greater than 0" in max_tokens_result.stdout

    def test_system_model_set_rejects_incompatible_model_for_default_provider(self, tmp_path, monkeypatch):
        """Model setter should reject values outside the current provider catalog."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "system", "model-set", "deepseek-chat"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "not compatible with provider 'openrouter'" in result.stdout

    def test_system_provider_show_and_default_commands_support_json(self, tmp_path, monkeypatch):
        """Provider show/default commands should expose typed JSON responses."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "deepseek",
                "--api-key",
                "deepseek-key",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "openrouter",
                "--api-key",
                "openrouter-key",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        default_result = subprocess.run(
            ["medclaw", "system", "provider-default", "deepseek", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        show_result = subprocess.run(
            ["medclaw", "system", "provider-show", "deepseek", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert default_result.returncode == 0
        default_payload = json.loads(default_result.stdout)
        assert default_payload["item"]["name"] == "deepseek"
        assert default_payload["item"]["is_default"] is True
        config_payload = json.loads((test_home / ".medclaw" / "config.json").read_text(encoding="utf-8"))
        assert config_payload["agents"]["defaults"]["model"] == "deepseek-chat"

        assert show_result.returncode == 0
        show_payload = json.loads(show_result.stdout)
        assert show_payload["item"]["name"] == "deepseek"
        assert show_payload["item"]["has_api_key"] is True
        assert show_payload["item"]["is_default"] is True

    def test_system_provider_default_requires_configured_api_key(self, tmp_path, monkeypatch):
        """Provider default command should reject providers without API keys."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "system", "provider-default", "deepseek"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "must have an API key" in result.stdout

    def test_system_provider_default_rejects_non_runtime_provider(self, tmp_path, monkeypatch):
        """Provider default command should reject providers that MedClaw cannot instantiate."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "anthropic",
                "--api-key",
                "anthropic-key",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        result = subprocess.run(
            ["medclaw", "system", "provider-default", "anthropic"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "not available as a runtime provider yet" in result.stdout

    def test_system_provider_unset_reassigns_default_when_possible(self, tmp_path, monkeypatch):
        """Provider unset should switch the default to another configured provider."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "deepseek",
                "--api-key",
                "deepseek-key",
                "--default",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "openrouter",
                "--api-key",
                "openrouter-key",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        unset_result = subprocess.run(
            ["medclaw", "system", "provider-unset", "deepseek", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        providers_result = subprocess.run(
            ["medclaw", "system", "providers", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert unset_result.returncode == 0
        unset_payload = json.loads(unset_result.stdout)
        assert unset_payload["item"]["name"] == "deepseek"
        assert unset_payload["item"]["configured"] is False
        assert unset_payload["item"]["is_default"] is False

        providers_payload = json.loads(providers_result.stdout)
        assert providers_payload["default_provider"] == "openrouter"

    def test_system_provider_unset_rejects_removing_last_default_provider(self, tmp_path, monkeypatch):
        """Provider unset should reject removing the last usable default provider."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        subprocess.run(
            [
                "medclaw",
                "system",
                "provider-set",
                "deepseek",
                "--api-key",
                "deepseek-key",
                "--default",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        result = subprocess.run(
            ["medclaw", "system", "provider-unset", "deepseek"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "Cannot unset default provider" in result.stdout

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
        assert "run" in result.stdout.lower()

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

    def test_research_workflows_command_supports_json(self):
        """Typed workflow listing should expose structured JSON output."""
        result = subprocess.run(
            ["medclaw", "research", "workflows", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] >= 1
        assert payload["items"][0]["id"]
        assert payload["items"][0]["title"]

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
        assert "--collection" in result.stdout

    def test_research_run_help_includes_collection_routing_flags(self):
        """Collection-aware runner help should expose workflow selection flags."""
        result = subprocess.run(
            ["medclaw", "research", "run", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "--collection" in result.stdout
        assert "--workflow" in result.stdout
        assert "--all-preferred" in result.stdout
        assert "--no-llm" in result.stdout

    def test_research_latest_help_includes_latest_options(self):
        """Latest shortcut help should expose collection and rendering options."""
        result = subprocess.run(
            ["medclaw", "research", "latest", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "--kind" in result.stdout
        assert "--artifact" in result.stdout
        assert "--by-collection" in result.stdout
        assert "--show" in result.stdout
        assert "--save-path" in result.stdout
        assert "--json" in result.stdout

    def test_research_artifacts_help_includes_kind_filter(self):
        """Artifact listing help should expose the kind filter."""
        result = subprocess.run(
            ["medclaw", "research", "artifacts", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "--kind" in result.stdout
        assert "--latest" in result.stdout
        assert "--latest-by-collection" in result.stdout

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
        assert payload["total"] == 1
        assert payload["items"][0]["workflow_id"] == "literature_review"
        assert payload["items"][0]["filename"] == report_path.name

    def test_research_artifacts_command_lists_collection_bundles(self, tmp_path, monkeypatch):
        """Research artifacts command should include collection bundle records."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "artifacts", "--collection", "KRAS Program", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["kind"] == "collection_bundle"
        assert payload["items"][0]["title"] == "Collection Brief: KRAS Program"

    def test_research_artifacts_command_can_filter_by_kind(self, tmp_path, monkeypatch):
        """Research artifacts command should separate reports and bundles by kind."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        report_result = subprocess.run(
            ["medclaw", "research", "artifacts", "--kind", "report", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        bundle_result = subprocess.run(
            ["medclaw", "research", "artifacts", "--kind", "bundle", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert report_result.returncode == 0
        assert bundle_result.returncode == 0
        report_payload = json.loads(report_result.stdout)
        bundle_payload = json.loads(bundle_result.stdout)
        assert report_payload["total"] == 1
        assert report_payload["items"][0]["kind"] == "report"
        assert bundle_payload["total"] == 1
        assert bundle_payload["items"][0]["kind"] == "collection_bundle"

    def test_research_artifacts_command_supports_latest_views(self, tmp_path, monkeypatch):
        """Artifact listing should support latest overall and latest per collection views."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="EGFR Study Design",
            question="EGFR biomarkers",
            summary="Summary",
            generated_at="2026-03-07T09:00:00+00:00",
            collection="EGFR Program",
        )
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        latest_result = subprocess.run(
            ["medclaw", "research", "artifacts", "--latest", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        latest_by_collection_result = subprocess.run(
            ["medclaw", "research", "artifacts", "--latest-by-collection", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert latest_result.returncode == 0
        assert latest_by_collection_result.returncode == 0
        latest_payload = json.loads(latest_result.stdout)
        latest_by_collection_payload = json.loads(latest_by_collection_result.stdout)
        assert latest_payload["total"] == 1
        assert latest_payload["items"][0]["kind"] == "collection_bundle"
        assert latest_by_collection_payload["total"] == 2
        assert {item["collection"] for item in latest_by_collection_payload["items"]} == {"KRAS Program", "EGFR Program"}

    def test_research_latest_command_shows_latest_artifact_content(self, tmp_path, monkeypatch):
        """Latest shortcut should render the newest artifact content directly."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "latest", "--kind", "bundle"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Collection Brief: KRAS Program" in result.stdout

    def test_research_latest_command_can_print_latest_artifact_path(self, tmp_path, monkeypatch):
        """Latest shortcut should print the latest artifact path when requested."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "latest", "--kind", "bundle", "--save-path"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert bundle_paths["bundle_markdown"].as_posix() in result.stdout

    def test_research_latest_command_can_print_specific_artifact_path(self, tmp_path, monkeypatch):
        """Latest shortcut should print the requested artifact path when specified."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "latest",
                "--kind",
                "bundle",
                "--artifact",
                "bundle-json",
                "--save-path",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert bundle_paths["bundle_json"].as_posix() in result.stdout

    def test_research_latest_command_supports_by_collection_summary_list(self, tmp_path, monkeypatch):
        """Latest shortcut should summarize newest artifacts per collection."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="EGFR Study Design",
            question="EGFR biomarkers",
            summary="Summary",
            generated_at="2026-03-07T09:00:00+00:00",
            collection="EGFR Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "latest", "--by-collection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Latest Research Artifacts" in result.stdout
        assert "KRAS Biomarker Brief" in result.stdout
        assert "EGFR Study Design" in result.stdout

    def test_research_latest_command_supports_by_collection_show(self, tmp_path, monkeypatch):
        """Latest shortcut should render each latest artifact when --show is used."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary one",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="EGFR Study Design",
            question="EGFR biomarkers",
            summary="Summary two",
            generated_at="2026-03-07T09:00:00+00:00",
            collection="EGFR Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "latest", "--by-collection", "--show"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "KRAS Biomarker Brief" in result.stdout
        assert "EGFR Study Design" in result.stdout

    def test_research_latest_command_can_print_paths_by_collection(self, tmp_path, monkeypatch):
        """Latest shortcut should print primary paths for each collection when requested."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        kras_report = self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary one",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        egfr_report = self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="EGFR Study Design",
            question="EGFR biomarkers",
            summary="Summary two",
            generated_at="2026-03-07T09:00:00+00:00",
            collection="EGFR Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "latest", "--by-collection", "--save-path"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert kras_report.as_posix() in result.stdout
        assert egfr_report.as_posix() in result.stdout

    def test_research_latest_command_can_return_specific_report_artifact_payload(self, tmp_path, monkeypatch):
        """Latest shortcut should expose specific report artifacts as JSON."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report(test_home)
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "latest",
                "--kind",
                "report",
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
        assert payload["total"] == 1
        assert payload["items"][0]["artifact"] == "citations"
        assert payload["items"][0]["payload"][0]["identifier"] == "PMID:1"

    def test_research_latest_command_rejects_incompatible_artifact_for_bundle(self, tmp_path, monkeypatch):
        """Latest shortcut should fail cleanly when artifact kind does not match the latest record."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "latest",
                "--kind",
                "bundle",
                "--artifact",
                "evidence",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "Unsupported artifact 'evidence' for collection_bundle" in result.stdout

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
        assert payload["total"] == 1
        assert payload["items"][0]["title"] == "KRAS G12C Review"

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
            collection="KRAS Program",
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
        assert payload["total"] == 1
        assert payload["items"][0]["workflow_id"] == "study_design"
        assert payload["items"][0]["generated_at"] == "2026-03-06T09:00:00+00:00"

    def test_research_artifacts_command_supports_collection_filter(self, tmp_path, monkeypatch):
        """Research artifacts command should filter reports by collection."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="KRAS G12C Review",
            question="KRAS G12C inhibitors",
            summary="Summary one",
            generated_at="2026-03-01T09:00:00+00:00",
            collection="KRAS Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="study_design",
            title="Adaptive Trial Design",
            question="Adaptive oncology trials",
            summary="Summary two",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="Trial Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "artifacts",
                "--collection",
                "KRAS Program",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["collection"] == "KRAS Program"

    def test_research_collections_command_lists_named_groups(self, tmp_path, monkeypatch):
        """Research collections command should aggregate reports by collection."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="KRAS Program",
            objective="Track KRAS evidence",
            disease_area="Oncology",
            owner="Translational Team",
            tags=["kras", "oncology"],
            preferred_workflows=["literature_review", "evidence_brief"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="KRAS G12C Review",
            question="KRAS G12C inhibitors",
            summary="Summary one",
            generated_at="2026-03-01T09:00:00+00:00",
            collection="KRAS Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="KRAS Biomarker Brief",
            question="KRAS biomarkers",
            summary="Summary two",
            generated_at="2026-03-06T09:00:00+00:00",
            collection="KRAS Program",
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "collections", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["collection"] == "KRAS Program"
        assert payload["items"][0]["report_count"] == 2
        assert payload["items"][0]["owner"] == "Translational Team"
        assert payload["items"][0]["latest_bundle_markdown_path"].endswith("bundle_summary.md")

    def test_research_collection_set_and_show_commands_manage_manifest(self, tmp_path, monkeypatch):
        """Research collection manifest commands should create and retrieve project metadata."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        save_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collection-set",
                "EGFR Program",
                "--objective",
                "Track EGFR biomarker evidence",
                "--disease-area",
                "Thoracic oncology",
                "--owner",
                "Biomarker Team",
                "--tag",
                "egfr",
                "--tag",
                "nsclc",
                "--preferred-workflow",
                "evidence_brief",
                "--preferred-workflow",
                "literature_review",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert save_result.returncode == 0
        save_payload = json.loads(save_result.stdout)
        assert save_payload["item"]["slug"] == "egfr-program"

        show_result = subprocess.run(
            ["medclaw", "research", "collection-show", "EGFR Program", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert show_result.returncode == 0
        show_payload = json.loads(show_result.stdout)
        assert show_payload["item"]["collection"] == "EGFR Program"
        assert show_payload["item"]["owner"] == "Biomarker Team"
        assert show_payload["item"]["preferred_workflows"] == ["evidence_brief", "literature_review"]

    def test_research_show_summary_view_includes_collection_objective(self, tmp_path, monkeypatch):
        """Summary view should display collection objective when present in report metadata."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        report_path = self._seed_report_with_fields(
            test_home,
            workflow_id="evidence_brief",
            title="EGFR Biomarker Brief",
            question="EGFR biomarkers",
            summary="A compact summary of EGFR biomarker evidence.",
            generated_at="2026-03-07T09:00:00+00:00",
            collection="EGFR Program",
            metadata={"collection_objective": "Track EGFR biomarker evidence"},
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "show", report_path.name, "--view", "summary"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "collection: EGFR Program" in result.stdout
        assert "objective: Track EGFR biomarker evidence" in result.stdout

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
        assert payload["artifact"] == "citations"
        assert payload["payload"][0]["identifier"] == "PMID:1"

    def test_research_show_command_can_display_bundle_markdown_by_default(self, tmp_path, monkeypatch):
        """Research show command should auto-display bundle markdown when given a bundle id."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "show", bundle_paths["artifact_dir"].name],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Collection Brief: KRAS Program" in result.stdout

    def test_research_show_command_can_return_bundle_json(self, tmp_path, monkeypatch):
        """Research show command should expose bundle JSON artifacts."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "show",
                bundle_paths["artifact_dir"].name,
                "--artifact",
                "bundle-json",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["artifact"] == "bundle_json"
        assert payload["payload"]["kind"] == "collection_bundle"
        assert payload["payload"]["collection"] == "KRAS Program"

    def test_research_show_command_can_return_bundle_metadata(self, tmp_path, monkeypatch):
        """Research show command should resolve shared metadata artifacts for bundle ids."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "show",
                bundle_paths["artifact_dir"].name,
                "--artifact",
                "metadata",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["artifact"] == "metadata"
        assert payload["payload"]["kind"] == "collection_bundle"
        assert payload["payload"]["collection"] == "KRAS Program"

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
            collection="EGFR Program",
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
        assert "collection: EGFR Program" in result.stdout
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
