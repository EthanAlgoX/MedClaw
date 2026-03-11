"""Evidence models and storage for MedClaw."""

from medclaw.evidence.artifacts import (
    BUNDLE_ARTIFACTS,
    CLI_ARTIFACTS,
    CLI_ARTIFACT_HELP,
    REPORT_ARTIFACTS,
    artifact_choices_for_kind,
    build_unsupported_artifact_error,
    format_artifact_choices,
    normalize_artifact_name,
)
from medclaw.evidence.api_models import (
    ArtifactListResponse,
    ArtifactPayloadListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    CollectionBundleArtifactRecord,
    ReportArtifactRecord,
    artifact_record_from_dict,
    artifact_records_from_dicts,
)
from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport
from medclaw.evidence.store import EvidenceStore

__all__ = [
    "ArtifactListResponse",
    "ArtifactPayloadListResponse",
    "ArtifactPayloadResponse",
    "ArtifactQueryFilters",
    "CollectionBundleArtifactRecord",
    "BUNDLE_ARTIFACTS",
    "CLI_ARTIFACTS",
    "CLI_ARTIFACT_HELP",
    "REPORT_ARTIFACTS",
    "ReportArtifactRecord",
    "Citation",
    "EvidenceItem",
    "ResearchReport",
    "EvidenceStore",
    "artifact_choices_for_kind",
    "artifact_record_from_dict",
    "artifact_records_from_dicts",
    "build_unsupported_artifact_error",
    "format_artifact_choices",
    "normalize_artifact_name",
]
