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
