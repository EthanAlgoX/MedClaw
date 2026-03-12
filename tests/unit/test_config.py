"""Unit tests for config module."""

import json
from pathlib import Path

import pytest

from medclaw.config.loader import (
    get_default_config_path,
    get_workspace_path,
    load_config,
    save_config,
)
from medclaw.config.schema import (
    AgentDefaultsConfig,
    AgentsConfig,
    ChannelExplainabilityConfig,
    ChannelsConfig,
    MedicalToolsConfig,
    MedClawConfig,
    ProviderConfig,
    ProvidersConfig,
    ToolsConfig,
    WorkspaceConfig,
)


class TestMedClawConfig:
    """Tests for MedClaw configuration."""

    def test_default_config_values(self):
        """Test that default config has correct values."""
        config = MedClawConfig()

        assert config.agents.defaults.provider == "openrouter"
        assert config.agents.defaults.model == "anthropic/claude-sonnet-4-20250514"
        assert config.agents.defaults.temperature == 0.1
        assert config.agents.defaults.maxTokens == 4096

    def test_custom_provider_config(self):
        """Test custom provider configuration."""
        config = MedClawConfig(
            providers=ProvidersConfig(
                deepseek=ProviderConfig(apiKey="test-key")
            ),
            agents=AgentsConfig(
                defaults=AgentDefaultsConfig(
                    provider="deepseek",
                    model="deepseek-chat"
                )
            )
        )

        assert config.providers.deepseek is not None
        assert config.providers.deepseek.apiKey == "test-key"
        assert config.agents.defaults.provider == "deepseek"

    def test_workspace_path_validation(self):
        """Test workspace path configuration."""
        custom_path = Path("/custom/workspace")
        config = MedClawConfig(
            workspace=WorkspaceConfig(path=custom_path)
        )

        assert config.workspace.path == custom_path

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        config = MedClawConfig.model_validate({
            "custom_field": "custom_value"
        })

        assert config.model_dump().get("custom_field") == "custom_value"

    def test_medical_tools_config(self):
        """Test medical tools configuration."""
        config = MedClawConfig(
            tools=ToolsConfig(
                medical=MedicalToolsConfig(
                    pubmedSource="ncbi",
                    drugSource="drugbank",
                    cacheTtlS=600,
                    maxResults=50
                )
            )
        )

        assert config.tools.medical.pubmedSource == "ncbi"
        assert config.tools.medical.drugSource == "drugbank"
        assert config.tools.medical.cacheTtlS == 600
        assert config.tools.medical.maxResults == 50

    def test_channels_config(self):
        """Test channels configuration."""
        config = MedClawConfig(
            channels=ChannelsConfig(
                explainabilityMode="verbose",
                explainabilityDelivery="auto"
            )
        )

        assert config.channels.explainabilityMode == "verbose"
        assert config.channels.explainabilityDelivery == "auto"


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_default_values(self):
        """Test default provider config values."""
        config = ProviderConfig()

        assert config.apiKey == ""
        assert config.baseUrl is None
        assert config.organization is None

    def test_custom_values(self):
        """Test custom provider config values."""
        config = ProviderConfig(
            apiKey="secret-key",
            baseUrl="https://custom.api.com",
            organization="org-123"
        )

        assert config.apiKey == "secret-key"
        assert config.baseUrl == "https://custom.api.com"
        assert config.organization == "org-123"


class TestLoadSaveConfig:
    """Tests for config loading and saving."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file."""
        return tmp_path / "config.json"

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        config = load_config(tmp_path / "nonexistent.json")

        assert isinstance(config, MedClawConfig)

    def test_save_and_load_config(self, temp_config_file):
        """Test saving and loading config."""
        config = MedClawConfig(
            providers=ProvidersConfig(
                deepseek=ProviderConfig(apiKey="test-key")
            )
        )

        save_config(config, temp_config_file)
        loaded = load_config(temp_config_file)

        assert loaded.providers is not None
        assert loaded.providers.deepseek is not None
        assert loaded.providers.deepseek.apiKey == "test-key"

    def test_load_config_invalid_json(self, temp_config_file):
        """Test loading invalid JSON returns default config."""
        temp_config_file.write_text("invalid json {")

        config = load_config(temp_config_file)

        assert isinstance(config, MedClawConfig)

    def test_get_default_config_path(self):
        """Test getting default config path."""
        path = get_default_config_path()

        assert "medclaw" in str(path)
        assert "config.json" in str(path)

    def test_get_workspace_path(self):
        """Test getting workspace path."""
        path = get_workspace_path()

        assert "medclaw" in str(path)
        assert "workspace" in str(path)

    def test_get_workspace_path_uses_configured_workspace(self, tmp_path, monkeypatch):
        """Configured workspace path should override the default location."""
        test_home = tmp_path / "test_home"
        test_home.mkdir()
        monkeypatch.setenv("HOME", str(test_home))

        configured_workspace = test_home / "custom-workspace"
        config = MedClawConfig(workspace=WorkspaceConfig(path=configured_workspace))
        save_config(config)

        path = get_workspace_path()

        assert path == configured_workspace
