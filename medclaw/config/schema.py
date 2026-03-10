"""Configuration schema for MedClaw."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderConfig(BaseModel):
    """LLM provider configuration."""

    apiKey: str = Field(default="")
    baseUrl: str | None = Field(default=None)
    organization: str | None = Field(default=None)


class ProvidersConfig(BaseModel):
    """All LLM providers configuration."""

    openai: ProviderConfig | None = Field(default=None)
    anthropic: ProviderConfig | None = Field(default=None)
    openrouter: ProviderConfig | None = Field(default=None)
    deepseek: ProviderConfig | None = Field(default=None)
    google: ProviderConfig | None = Field(default=None)


class AgentDefaultsConfig(BaseModel):
    """Default agent configuration."""

    provider: str = Field(default="openrouter")
    model: str = Field(default="anthropic/claude-sonnet-4-20250514")
    temperature: float = Field(default=0.1)
    maxTokens: int = Field(default=4096)


class AgentsConfig(BaseModel):
    """Agents configuration."""

    defaults: AgentDefaultsConfig = Field(default_factory=AgentDefaultsConfig)


class MedicalToolsConfig(BaseModel):
    """Medical tools configuration."""

    pubmedSource: str = Field(default="ncbi")
    drugSource: str = Field(default="drugbank")
    cacheTtlS: int = Field(default=300)
    maxResults: int = Field(default=20)


class ToolsConfig(BaseModel):
    """Tools configuration."""

    medical: MedicalToolsConfig = Field(default_factory=MedicalToolsConfig)


class ChannelExplainabilityConfig(BaseModel):
    """Channel explainability configuration."""

    mode: str = Field(default="auto")
    delivery: str = Field(default="auto")


class ChannelsConfig(BaseModel):
    """Channels configuration."""

    explainabilityMode: str = Field(default="auto")
    explainabilityDelivery: str = Field(default="auto")


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""

    path: Path = Field(default=Path.home() / ".medclaw" / "workspace")
    memoryPath: Path | None = Field(default=None)
    reportsPath: Path | None = Field(default=None)


class MedClawConfig(BaseModel):
    """Main MedClaw configuration."""

    model_config = ConfigDict(extra="allow")

    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
