"""Shared artifact schema and validation helpers."""

from __future__ import annotations

from typing import Iterable

REPORT_ARTIFACTS = ("report", "evidence", "citations", "metadata")
BUNDLE_ARTIFACTS = ("bundle_markdown", "bundle_json", "metadata")
REPORT_PATH_ARTIFACTS = REPORT_ARTIFACTS + ("artifact_dir",)
BUNDLE_PATH_ARTIFACTS = BUNDLE_ARTIFACTS + ("artifact_dir",)
CLI_ARTIFACTS = ("report", "evidence", "citations", "metadata", "bundle_markdown", "bundle_json")
CLI_ARTIFACT_HELP = (
    "Specific artifact: report, evidence, citations, metadata, bundle-markdown, bundle-json."
)


def format_artifact_choices(choices: Iterable[str]) -> str:
    """Render artifact names with CLI-friendly separators."""
    return ", ".join(choice.replace("_", "-") for choice in choices)


def build_unsupported_artifact_error(
    artifact: str,
    choices: Iterable[str],
    *,
    kind: str | None = None,
) -> ValueError:
    """Build a consistent unsupported-artifact error."""
    label = artifact.strip() if artifact.strip() else artifact
    message = f"Unsupported artifact '{label}'."
    if kind:
        message = f"Unsupported artifact '{label}' for {kind}."
    return ValueError(f"{message} Choose from: {format_artifact_choices(choices)}")


def normalize_artifact_name(
    artifact: str | None,
    *,
    choices: Iterable[str] | None = None,
    kind: str | None = None,
) -> str | None:
    """Normalize an artifact option and optionally validate it."""
    if artifact is None:
        return None

    normalized = artifact.strip().lower().replace("-", "_")
    if choices is None:
        return normalized
    allowed = tuple(choices)
    if normalized not in allowed:
        raise build_unsupported_artifact_error(artifact, allowed, kind=kind)
    return normalized


def artifact_choices_for_kind(kind: str, *, include_internal: bool = False) -> tuple[str, ...]:
    """Return supported artifact names for a report or bundle record."""
    normalized_kind = kind.strip().lower()
    if normalized_kind == "report":
        return REPORT_PATH_ARTIFACTS if include_internal else REPORT_ARTIFACTS
    if normalized_kind in {"bundle", "collection_bundle"}:
        return BUNDLE_PATH_ARTIFACTS if include_internal else BUNDLE_ARTIFACTS
    raise ValueError(f"Unsupported artifact kind: {kind}")
