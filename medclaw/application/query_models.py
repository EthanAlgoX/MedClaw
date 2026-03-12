"""Typed query models for workflow and skill discovery outputs."""

from __future__ import annotations

from pydantic import BaseModel


class WorkflowSummary(BaseModel):
    """Compact workflow summary."""

    id: str
    title: str


class WorkflowListResponse(BaseModel):
    """Typed workflow listing response."""

    items: list[WorkflowSummary]
    total: int


class SkillSummary(BaseModel):
    """Compact skill summary used for listing and search."""

    name: str
    path: str
    source: str
    description: str = ""
    relevance_score: str = ""
    reasons: str = ""


class SkillListResponse(BaseModel):
    """Typed skill listing/search response."""

    items: list[SkillSummary]
    total: int
    query: str | None = None


class ProviderSummary(BaseModel):
    """Compact provider configuration summary."""

    name: str
    configured: bool
    has_api_key: bool
    base_url: str | None = None
    organization: str | None = None
    is_default: bool = False


class ProviderListResponse(BaseModel):
    """Typed provider listing response."""

    items: list[ProviderSummary]
    total: int
    default_provider: str


class ProviderResponse(BaseModel):
    """Typed single-provider response."""

    item: ProviderSummary


class WorkspaceSummary(BaseModel):
    """Workspace layout summary."""

    path: str
    exists: bool
    skills_path: str
    memory_path: str
    reports_path: str
    research_path: str
    collections_path: str


class WorkspaceResponse(BaseModel):
    """Typed workspace summary response."""

    item: WorkspaceSummary


class ConfigSummary(BaseModel):
    """Top-level configuration summary."""

    config_path: str
    workspace: WorkspaceSummary
    default_provider: str
    default_model: str
    temperature: float
    max_tokens: int
    providers: list[ProviderSummary]


class ConfigResponse(BaseModel):
    """Typed config summary response."""

    item: ConfigSummary
