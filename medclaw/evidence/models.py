"""Structured evidence models for medical research workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A normalized citation for a medical evidence item."""

    source: str
    title: str
    identifier: str | None = None
    url: str | None = None
    published_at: str | None = None


class EvidenceItem(BaseModel):
    """A normalized evidence object produced by a source adapter."""

    id: str
    kind: str
    source: str
    title: str
    summary: str = ""
    citations: list[Citation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchReport(BaseModel):
    """A saved output from a MedClaw research workflow."""

    workflow_id: str
    question: str
    title: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    disclaimer: str = ""
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseModel):
    """Execution metadata for one workflow invocation."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    workflow_id: str
    question: str
    status: str = "completed"
    llm_enabled: bool = False
    provider_name: str = ""
    model_name: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    report_path: str = ""
    artifact_dir: str = ""
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchRun(BaseModel):
    """Execution metadata for one research run."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    query: str
    collection: str = ""
    status: str = "completed"
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    workflow_runs: list[WorkflowRun] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
