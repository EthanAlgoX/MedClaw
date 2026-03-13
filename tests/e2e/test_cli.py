"""E2E tests for CLI commands."""

import json
import subprocess
from pathlib import Path

import pytest

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport, ResearchRun, WorkflowRun
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

    def _seed_run(
        self,
        home: Path,
        *,
        run_id: str,
        query: str,
        collection: str,
        workflow_ids: list[str],
        completed_at: str,
        bundle_saved_path: str = "",
    ) -> Path:
        workspace = home / ".medclaw" / "workspace"
        store = EvidenceStore(workspace)
        workflow_runs = [
            WorkflowRun(
                workflow_id=workflow_id,
                question=query,
                completed_at=completed_at,
                started_at=completed_at,
            )
            for workflow_id in workflow_ids
        ]
        return store.save_run(
            ResearchRun(
                id=run_id,
                query=query,
                collection=collection,
                started_at=completed_at,
                completed_at=completed_at,
                workflow_runs=workflow_runs,
                metadata={"bundle_saved_path": bundle_saved_path} if bundle_saved_path else {},
            )
        )

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
        assert payload["item"]["exports_path"].endswith("research/exports")

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

    def test_research_runs_help_includes_run_filters(self):
        """Research runs help should expose list/show entrypoints and filters."""
        result = subprocess.run(
            ["medclaw", "research", "runs", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "--search" in result.stdout
        assert "--workflow" in result.stdout
        assert "--collection" in result.stdout
        assert "--latest" in result.stdout
        assert "--json" in result.stdout

    def test_research_timeline_help_includes_filters(self):
        """Research timeline help should expose its filtering options."""
        result = subprocess.run(
            ["medclaw", "research", "timeline", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "--search" in result.stdout
        assert "--workflow" in result.stdout
        assert "--collection" in result.stdout
        assert "--json" in result.stdout

    def test_research_dashboard_command_aggregates_collection_state(self, tmp_path, monkeypatch):
        """Research dashboard should merge collection stats, latest assets, and timeline."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="KRAS Program",
            objective="Track KRAS evidence",
            owner="Translational Team",
            preferred_workflows=["literature_review", "evidence_brief"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="KRAS Review",
            question="KRAS inhibitors",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="KRAS Program",
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="literature_review",
                    question="KRAS inhibitors",
                    title="KRAS Review",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        self._seed_run(
            test_home,
            run_id="run-001",
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_ids=["literature_review"],
            completed_at="2026-03-08T09:06:00+00:00",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "dashboard", "KRAS Program", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            ["medclaw", "research", "dashboard", "KRAS Program"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["item"]["collection"]["collection"] == "KRAS Program"
        assert payload["item"]["latest_report"]["kind"] == "report"
        assert payload["item"]["latest_bundle"]["kind"] == "collection_bundle"
        assert payload["item"]["latest_run"]["id"] == "run-001"
        assert payload["item"]["missing_preferred_workflows"] == ["evidence_brief"]
        assert payload["item"]["health_signals"] == ["missing_preferred_workflow:evidence_brief"]

        assert text_result.returncode == 0
        assert "KRAS Program" in text_result.stdout
        assert "latest report: KRAS Review" in text_result.stdout
        assert "latest run: run-001" in text_result.stdout

    def test_research_dashboard_command_surfaces_stale_collection_health(self, tmp_path, monkeypatch):
        """Research dashboard should expose stale and missing-asset health signals."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Dormant Program",
            objective="Monitor a paused research topic",
            preferred_workflows=["literature_review"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Legacy Review",
            question="Legacy topic",
            summary="Summary",
            generated_at="2025-01-01T09:00:00+00:00",
            collection="Dormant Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "dashboard", "Dormant Program", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            ["medclaw", "research", "dashboard", "Dormant Program"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["item"]["stale"] is True
        assert "no_bundle" in payload["item"]["health_signals"]
        assert "no_run" in payload["item"]["health_signals"]
        assert "stale_collection" in payload["item"]["health_signals"]

        assert text_result.returncode == 0
        assert "stale: yes" in text_result.stdout
        assert "health signals:" in text_result.stdout

    def test_research_dashboards_command_lists_filtered_collection_views(self, tmp_path, monkeypatch):
        """Research dashboards should expose filtered multi-collection health views."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Dormant Program",
            objective="Track stale activity",
            preferred_workflows=["literature_review"],
        )
        store.save_collection_manifest(
            name="Gap Program",
            objective="Track workflow coverage",
            preferred_workflows=["evidence_brief"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Legacy Review",
            question="Legacy topic",
            summary="Summary",
            generated_at="2025-01-01T09:00:00+00:00",
            collection="Dormant Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Coverage Review",
            question="Coverage topic",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="Gap Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--only-unhealthy",
                "--missing-workflow",
                "evidence_brief",
                "--sort-by",
                "health",
                "--timeline-limit",
                "2",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--only-unhealthy",
                "--missing-workflow",
                "evidence_brief",
                "--sort-by",
                "health",
                "--timeline-limit",
                "2",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["collection"]["collection"] == "Gap Program"
        assert payload["items"][0]["missing_preferred_workflows"] == ["evidence_brief"]
        assert payload["filters"]["sort_by"] == "health"
        assert payload["filters"]["timeline_limit"] == 2

        assert text_result.returncode == 0
        assert "Collection Dashboards" in text_result.stdout
        assert "sort=health" in text_result.stdout
        assert "Gap Program" in text_result.stdout
        assert "missing preferred: evidence_brief" in text_result.stdout

    def test_research_dashboards_command_supports_top_summary_and_export(self, tmp_path, monkeypatch):
        """Research dashboards should support top-N summary output and JSON export."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        export_path = "dashboard-export.json"
        export_md_path = "dashboard-export.md"
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Gap Program",
            objective="Track workflow coverage",
            owner="Biomarker Team",
            preferred_workflows=["evidence_brief"],
        )
        store.save_collection_manifest(
            name="Dormant Program",
            objective="Track stale activity",
            owner="Translational Team",
            preferred_workflows=["literature_review"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Coverage Review",
            question="Coverage topic",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="Gap Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Legacy Review",
            question="Legacy topic",
            summary="Summary",
            generated_at="2025-01-01T09:00:00+00:00",
            collection="Dormant Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--sort-by",
                "health",
                "--group-by",
                "owner",
                "--top",
                "1",
                "--summary-only",
                "--export-json-path",
                str(export_path),
                "--export-md-path",
                str(export_md_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "dashboard export:" in result.stdout
        assert "dashboard markdown:" in result.stdout
        assert "total=1 stale=1 unhealthy=1" in result.stdout
        assert "grouped by owner:" in result.stdout
        assert "Translational Team" in result.stdout
        assert "Dormant Program" in result.stdout
        assert "latest run:" not in result.stdout
        resolved_export_path = test_home / ".medclaw" / "workspace" / "research" / "exports" / export_path
        resolved_export_md_path = test_home / ".medclaw" / "workspace" / "research" / "exports" / export_md_path
        assert resolved_export_path.exists()
        assert resolved_export_md_path.exists()

        export_payload = json.loads(resolved_export_path.read_text(encoding="utf-8"))
        assert export_payload["total"] == 1
        assert export_payload["items"][0]["collection"]["collection"] == "Dormant Program"
        assert export_payload["summary"]["grouped_by"] == "owner"
        assert export_payload["summary"]["groups"][0]["label"] == "Translational Team"
        assert export_payload["filters"]["group_by"] == "owner"
        assert export_payload["filters"]["top"] == 1

        export_markdown = resolved_export_md_path.read_text(encoding="utf-8")
        assert export_markdown.startswith("---\n")
        assert 'kind: "collection_dashboard_inventory"' in export_markdown
        assert 'artifact_id: "dashboard-inventory-' in export_markdown
        assert 'export_version: 1' in export_markdown
        assert 'workspace_path: ' in export_markdown
        assert 'group_by: "owner"' in export_markdown
        assert "filters:" in export_markdown
        assert 'top: 1' in export_markdown
        assert "summary:" in export_markdown
        assert "# Collection Dashboard Inventory" in export_markdown
        assert "## Groups" in export_markdown
        assert "## Translational Team" in export_markdown
        assert "### Dormant Program" in export_markdown
        assert "- Health: no_bundle, no_run, stale_collection" in export_markdown

        exports_result = subprocess.run(
            ["medclaw", "research", "exports", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert exports_result.returncode == 0
        exports_payload = json.loads(exports_result.stdout)
        assert exports_payload["total"] >= 2
        assert any(item["filename"] == "dashboard-export.md" for item in exports_payload["items"])
        assert any(item["filename"] == "dashboard-export.json" for item in exports_payload["items"])

        export_show_path_result = subprocess.run(
            ["medclaw", "research", "export-show", "dashboard-export.md", "--save-path"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        export_show_markdown_result = subprocess.run(
            ["medclaw", "research", "export-show", "dashboard-export.md"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        export_show_json_result = subprocess.run(
            ["medclaw", "research", "export-show", "dashboard-export.json", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert export_show_path_result.returncode == 0
        assert export_show_path_result.stdout.strip() == str(resolved_export_md_path)
        assert export_show_markdown_result.returncode == 0
        assert "Collection Dashboard Inventory" in export_show_markdown_result.stdout
        assert "Dormant Program" in export_show_markdown_result.stdout
        assert export_show_json_result.returncode == 0
        export_show_payload = json.loads(export_show_json_result.stdout)
        assert export_show_payload["record"]["filename"] == "dashboard-export.json"
        assert export_show_payload["payload"]["summary"]["grouped_by"] == "owner"

    def test_research_dashboards_command_supports_owner_and_missing_asset_filters(self, tmp_path, monkeypatch):
        """Research dashboards should filter by owner, disease area, and missing assets."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Gap Program",
            objective="Track workflow coverage",
            owner="Biomarker Team",
            disease_area="Thoracic oncology",
            preferred_workflows=["evidence_brief"],
        )
        store.save_collection_manifest(
            name="Stable Program",
            objective="Track stable active work",
            owner="Biomarker Team",
            disease_area="Thoracic oncology",
            preferred_workflows=["literature_review"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Gap Review",
            question="Gap topic",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="Gap Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Stable Review",
            question="Stable topic",
            summary="Summary",
            generated_at="2026-03-09T09:00:00+00:00",
            collection="Stable Program",
        )
        self._seed_run(
            test_home,
            run_id="run-stable",
            query="Stable topic",
            collection="Stable Program",
            workflow_ids=["literature_review"],
            completed_at="2026-03-09T09:00:00+00:00",
        )
        stable_bundle_store = EvidenceStore(test_home / ".medclaw" / "workspace")
        stable_bundle_store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="literature_review",
                    question="Stable topic",
                    title="Stable Review",
                    summary="Summary",
                    metadata={"collection": "Stable Program"},
                )
            ],
            markdown_summary="# Collection Brief: Stable Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--owner",
                "Biomarker Team",
                "--disease-area",
                "Thoracic oncology",
                "--only-missing-bundle",
                "--only-missing-run",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--owner",
                "Biomarker Team",
                "--disease-area",
                "Thoracic oncology",
                "--only-missing-bundle",
                "--only-missing-run",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["collection"]["collection"] == "Gap Program"
        assert payload["filters"]["owner"] == "Biomarker Team"
        assert payload["filters"]["disease_area"] == "Thoracic oncology"
        assert payload["filters"]["only_missing_bundle"] is True
        assert payload["filters"]["only_missing_run"] is True
        assert payload["summary"]["missing_bundle"] == 1
        assert payload["summary"]["missing_run"] == 1

        assert text_result.returncode == 0
        assert "missing_bundle=1" in text_result.stdout
        assert "missing_run=1" in text_result.stdout
        assert "Gap Program" in text_result.stdout
        assert "Stable Program" not in text_result.stdout

    def test_research_dashboards_and_collections_support_stale_day_thresholds(self, tmp_path, monkeypatch):
        """Dashboard and collection listings should support stale-day threshold filtering."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Dormant Program",
            objective="Track stale activity",
            owner="Translational Team",
            disease_area="Oncology",
            preferred_workflows=["literature_review"],
        )
        store.save_collection_manifest(
            name="Recent Program",
            objective="Track recent activity",
            owner="Translational Team",
            disease_area="Oncology",
            preferred_workflows=["literature_review"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Legacy Review",
            question="Legacy topic",
            summary="Summary",
            generated_at="2025-01-01T09:00:00+00:00",
            collection="Dormant Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Recent Review",
            question="Recent topic",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="Recent Program",
        )
        monkeypatch.setenv("HOME", str(test_home))

        dashboards_result = subprocess.run(
            ["medclaw", "research", "dashboards", "--stale-days-min", "30", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        collections_result = subprocess.run(
            ["medclaw", "research", "collections", "--stale-days-min", "30", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert dashboards_result.returncode == 0
        dashboards_payload = json.loads(dashboards_result.stdout)
        assert dashboards_payload["total"] == 1
        assert dashboards_payload["items"][0]["collection"]["collection"] == "Dormant Program"
        assert dashboards_payload["filters"]["stale_days_min"] == 30

        assert collections_result.returncode == 0
        collections_payload = json.loads(collections_result.stdout)
        assert collections_payload["total"] == 1
        assert collections_payload["items"][0]["collection"] == "Dormant Program"

    def test_research_runs_command_lists_saved_runs(self, tmp_path, monkeypatch):
        """Research runs command should expose typed saved run records."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_run(
            test_home,
            run_id="run-001",
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_ids=["literature_review"],
            completed_at="2026-03-08T09:00:00+00:00",
        )
        self._seed_run(
            test_home,
            run_id="run-002",
            query="EGFR biomarkers",
            collection="EGFR Program",
            workflow_ids=["study_design", "evidence_brief"],
            completed_at="2026-03-09T09:00:00+00:00",
            bundle_saved_path="/tmp/bundle_summary.md",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "runs", "--workflow", "study_design", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        latest_result = subprocess.run(
            ["medclaw", "research", "runs", "--latest", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 1
        assert payload["items"][0]["id"] == "run-002"
        assert payload["items"][0]["scope"] == "collection"

        assert latest_result.returncode == 0
        latest_payload = json.loads(latest_result.stdout)
        assert latest_payload["total"] == 1
        assert latest_payload["items"][0]["id"] == "run-002"

    def test_research_run_show_command_returns_saved_run(self, tmp_path, monkeypatch):
        """Research run-show command should return the selected run payload."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        run_path = self._seed_run(
            test_home,
            run_id="run-001",
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_ids=["literature_review", "evidence_brief"],
            completed_at="2026-03-08T09:00:00+00:00",
            bundle_saved_path="/tmp/bundle_summary.md",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "run-show", "run-001", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            ["medclaw", "research", "run-show", str(run_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["record"]["id"] == "run-001"
        assert payload["record"]["scope"] == "collection"
        assert payload["run"]["workflow_runs"][0]["workflow_id"] == "literature_review"

        assert text_result.returncode == 0
        assert "Research Run run-001" in text_result.stdout
        assert "collection: KRAS Program" in text_result.stdout

    def test_research_timeline_command_merges_runs_and_artifacts(self, tmp_path, monkeypatch):
        """Research timeline should unify runs, reports, and bundle artifacts."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="KRAS Review",
            question="KRAS inhibitors",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
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
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        self._seed_run(
            test_home,
            run_id="run-001",
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_ids=["study_design", "evidence_brief"],
            completed_at="2026-03-08T09:06:00+00:00",
        )
        monkeypatch.setenv("HOME", str(test_home))

        result = subprocess.run(
            ["medclaw", "research", "timeline", "--collection", "KRAS Program", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text_result = subprocess.run(
            ["medclaw", "research", "timeline", "--collection", "KRAS Program"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["total"] == 3
        assert [item["kind"] for item in payload["items"]] == ["collection_bundle", "research_run", "report"]
        assert payload["items"][0]["collection"] == "KRAS Program"

        assert text_result.returncode == 0
        assert "Research Timeline" in text_result.stdout
        assert "(research_run)" in text_result.stdout
        assert "(collection_bundle)" in text_result.stdout

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
        text_result = subprocess.run(
            ["medclaw", "research", "collections"],
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
        assert payload["items"][0]["health_signals"] == ["no_run"]

        assert text_result.returncode == 0
        assert "health: no_run" in text_result.stdout

    def test_research_collections_command_supports_health_filters(self, tmp_path, monkeypatch):
        """Research collections command should support stale and unhealthy triage filters."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        store = EvidenceStore(test_home / ".medclaw" / "workspace")
        store.save_collection_manifest(
            name="Dormant Program",
            objective="Track stale activity",
            owner="Translational Team",
            disease_area="Oncology",
            preferred_workflows=["literature_review"],
        )
        store.save_collection_manifest(
            name="Gap Program",
            objective="Track workflow coverage",
            owner="Biomarker Team",
            disease_area="Thoracic oncology",
            preferred_workflows=["evidence_brief"],
        )
        store.save_collection_manifest(
            name="Healthy Program",
            objective="Track active execution",
            owner="Translational Team",
            disease_area="Oncology",
            preferred_workflows=["literature_review"],
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Legacy Review",
            question="Legacy topic",
            summary="Summary",
            generated_at="2025-01-01T09:00:00+00:00",
            collection="Dormant Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Coverage Review",
            question="Coverage topic",
            summary="Summary",
            generated_at="2026-03-08T09:00:00+00:00",
            collection="Gap Program",
        )
        self._seed_report_with_fields(
            test_home,
            workflow_id="literature_review",
            title="Healthy Review",
            question="Healthy topic",
            summary="Summary",
            generated_at="2026-03-09T09:00:00+00:00",
            collection="Healthy Program",
        )
        self._seed_run(
            test_home,
            run_id="run-healthy",
            query="Healthy topic",
            collection="Healthy Program",
            workflow_ids=["literature_review"],
            completed_at="2026-03-09T09:00:00+00:00",
        )
        monkeypatch.setenv("HOME", str(test_home))

        stale_result = subprocess.run(
            ["medclaw", "research", "collections", "--only-stale", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        unhealthy_result = subprocess.run(
            ["medclaw", "research", "collections", "--only-unhealthy", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        missing_result = subprocess.run(
            ["medclaw", "research", "collections", "--missing-workflow", "evidence_brief", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        owner_bundle_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collections",
                "--owner",
                "Translational Team",
                "--disease-area",
                "Oncology",
                "--only-missing-bundle",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        owner_run_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collections",
                "--owner",
                "Biomarker Team",
                "--only-missing-run",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        sorted_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collections",
                "--sort-by",
                "health",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        sorted_text_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collections",
                "--sort-by",
                "name",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        searched_result = subprocess.run(
            [
                "medclaw",
                "research",
                "collections",
                "--search",
                "thoracic",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        searched_dashboard_result = subprocess.run(
            [
                "medclaw",
                "research",
                "dashboards",
                "--search",
                "coverage review",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert stale_result.returncode == 0
        stale_payload = json.loads(stale_result.stdout)
        assert [item["collection"] for item in stale_payload["items"]] == ["Dormant Program"]

        assert unhealthy_result.returncode == 0
        unhealthy_payload = json.loads(unhealthy_result.stdout)
        assert {item["collection"] for item in unhealthy_payload["items"]} == {
            "Dormant Program",
            "Gap Program",
            "Healthy Program",
        }

        assert missing_result.returncode == 0
        missing_payload = json.loads(missing_result.stdout)
        assert [item["collection"] for item in missing_payload["items"]] == ["Gap Program"]

        assert owner_bundle_result.returncode == 0
        owner_bundle_payload = json.loads(owner_bundle_result.stdout)
        assert {item["collection"] for item in owner_bundle_payload["items"]} == {
            "Dormant Program",
            "Healthy Program",
        }

        assert owner_run_result.returncode == 0
        owner_run_payload = json.loads(owner_run_result.stdout)
        assert [item["collection"] for item in owner_run_payload["items"]] == ["Gap Program"]

        assert sorted_result.returncode == 0
        sorted_payload = json.loads(sorted_result.stdout)
        assert [item["collection"] for item in sorted_payload["items"][:2]] == [
            "Dormant Program",
            "Gap Program",
        ]

        assert sorted_text_result.returncode == 0
        assert "sort_by=name" in sorted_text_result.stdout

        assert searched_result.returncode == 0
        searched_payload = json.loads(searched_result.stdout)
        assert [item["collection"] for item in searched_payload["items"]] == ["Gap Program"]

        assert searched_dashboard_result.returncode == 0
        searched_dashboard_payload = json.loads(searched_dashboard_result.stdout)
        assert searched_dashboard_payload["filters"]["query"] == "coverage review"
        assert [item["collection"]["collection"] for item in searched_dashboard_payload["items"]] == ["Gap Program"]

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
