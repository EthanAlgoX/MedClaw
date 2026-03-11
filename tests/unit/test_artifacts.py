"""Unit tests for shared artifact schema helpers."""

from medclaw.evidence.artifacts import (
    CLI_ARTIFACTS,
    BUNDLE_ARTIFACTS,
    REPORT_ARTIFACTS,
    artifact_choices_for_kind,
    normalize_artifact_name,
)


class TestArtifactSchema:
    """Tests for shared artifact schema helpers."""

    def test_normalize_artifact_name_accepts_cli_spellings(self):
        assert normalize_artifact_name("bundle-json", choices=CLI_ARTIFACTS) == "bundle_json"
        assert normalize_artifact_name(" metadata ", choices=CLI_ARTIFACTS) == "metadata"

    def test_normalize_artifact_name_rejects_unknown_values(self):
        try:
            normalize_artifact_name("raw", choices=CLI_ARTIFACTS)
        except ValueError as exc:
            assert "Unsupported artifact 'raw'" in str(exc)
        else:
            raise AssertionError("Expected ValueError for unsupported artifact")

    def test_artifact_choices_for_kind_returns_expected_schema(self):
        assert artifact_choices_for_kind("report") == REPORT_ARTIFACTS
        assert artifact_choices_for_kind("bundle") == BUNDLE_ARTIFACTS
        assert artifact_choices_for_kind("collection_bundle") == BUNDLE_ARTIFACTS
