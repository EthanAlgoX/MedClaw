"""Unit tests for typed artifact API models."""

from medclaw.evidence.api_models import (
    ArtifactListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    artifact_record_from_dict,
)


class TestArtifactApiModels:
    """Tests for typed artifact API envelopes."""

    def test_artifact_record_from_dict_supports_report_and_bundle_shapes(self):
        report_record = artifact_record_from_dict(
            {
                "kind": "report",
                "id": "report.json",
                "path": "/tmp/report.json",
                "filename": "report.json",
                "collection": "KRAS Program",
                "workflow_id": "literature_review",
                "title": "KRAS Review",
                "question": "KRAS inhibitors",
                "generated_at": "2026-03-08T09:00:00+00:00",
                "evidence_count": 3,
                "citation_count": 2,
                "summary_preview": "Summary",
                "artifact_dir": "/tmp/report_artifacts",
            }
        )
        bundle_record = artifact_record_from_dict(
            {
                "kind": "collection_bundle",
                "id": "bundle_artifacts",
                "path": "/tmp/bundle_artifacts",
                "filename": "bundle_artifacts",
                "collection": "KRAS Program",
                "workflow_id": "collection_bundle",
                "title": "Collection Brief: KRAS Program",
                "question": "",
                "generated_at": "2026-03-08T09:00:00+00:00",
                "evidence_count": 5,
                "citation_count": 4,
                "summary_preview": "Summary",
                "artifact_dir": "/tmp/bundle_artifacts",
                "bundle_markdown_path": "/tmp/bundle_artifacts/bundle_summary.md",
                "bundle_json_path": "/tmp/bundle_artifacts/bundle_summary.json",
                "report_count": 2,
                "workflow_ids": ["study_design", "evidence_brief"],
            }
        )

        assert report_record.kind == "report"
        assert bundle_record.kind == "collection_bundle"

    def test_artifact_response_models_dump_typed_envelopes(self):
        filters = ArtifactQueryFilters(kind="report", latest=True, limit=1)
        record = artifact_record_from_dict(
            {
                "kind": "report",
                "id": "report.json",
                "path": "/tmp/report.json",
                "filename": "report.json",
                "collection": "",
                "workflow_id": "evidence_brief",
                "title": "Biomarker Brief",
                "question": "EGFR biomarkers",
                "generated_at": "2026-03-08T09:00:00+00:00",
                "evidence_count": 1,
                "citation_count": 1,
                "summary_preview": "Summary",
                "artifact_dir": "/tmp/report_artifacts",
            }
        )
        list_response = ArtifactListResponse(items=[record], total=1, filters=filters)
        payload_response = ArtifactPayloadResponse(
            target="report.json",
            artifact="citations",
            kind="report",
            path="/tmp/report_artifacts/citations.json",
            format="json",
            record=record,
            payload=[
                {
                    "source": "pubmed",
                    "title": "Biomarker paper",
                    "identifier": "PMID:1",
                }
            ],
        )

        assert list_response.model_dump(mode="json")["items"][0]["kind"] == "report"
        assert payload_response.model_dump(mode="json")["artifact"] == "citations"
