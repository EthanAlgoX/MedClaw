"""Unit tests for typed artifact API models."""

from medclaw.evidence.api_models import (
    ArtifactListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    CollectionListResponse,
    CollectionResponse,
    ResearchRunListResponse,
    ResearchRunQueryFilters,
    ResearchRunResponse,
    ResearchReportListResponse,
    ResearchReportResponse,
    artifact_record_from_dict,
    research_run_record_from_dict,
)
from medclaw.evidence.models import ResearchReport, ResearchRun, WorkflowRun


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

    def test_report_and_collection_response_models_dump_envelopes(self):
        report = ResearchReport(
            workflow_id="evidence_brief",
            question="EGFR biomarkers",
            title="Biomarker Brief",
            summary="Summary",
        )
        report_response = ResearchReportResponse(report=report)
        report_list_response = ResearchReportListResponse(items=[report], total=1)
        collection_response = CollectionResponse(
            item={
                "collection": "EGFR Program",
                "slug": "egfr-program",
                "objective": "Track EGFR biomarker evidence",
                "disease_area": "Thoracic oncology",
                "owner": "Biomarker Team",
                "tags": ["egfr"],
                "preferred_workflows": ["evidence_brief"],
                "created_at": "",
                "updated_at": "",
                "report_count": 1,
                "evidence_count": 2,
                "citation_count": 2,
                "latest_generated_at": "2026-03-08T09:00:00+00:00",
                "latest_bundle_generated_at": "",
                "latest_bundle_markdown_path": "",
                "latest_bundle_json_path": "",
                "workflows": ["evidence_brief"],
                "titles": ["Biomarker Brief"],
            }
        )
        collection_list_response = CollectionListResponse(items=[collection_response.item], total=1, limit=20)

        assert report_response.model_dump(mode="json")["report"]["workflow_id"] == "evidence_brief"
        assert report_list_response.model_dump(mode="json")["total"] == 1
        assert collection_response.model_dump(mode="json")["item"]["slug"] == "egfr-program"
        assert collection_list_response.model_dump(mode="json")["items"][0]["collection"] == "EGFR Program"

    def test_research_run_response_models_dump_envelopes(self):
        record = research_run_record_from_dict(
            {
                "id": "run-123",
                "path": "/tmp/run-123.json",
                "filename": "20260308_run-123.json",
                "scope": "collection",
                "query": "KRAS inhibitors",
                "collection": "KRAS Program",
                "status": "completed",
                "started_at": "2026-03-08T09:00:00+00:00",
                "completed_at": "2026-03-08T09:10:00+00:00",
                "workflow_count": 2,
                "workflow_ids": ["study_design", "evidence_brief"],
                "bundle_saved_path": "/tmp/bundle_summary.md",
            }
        )
        run = ResearchRun(
            id="run-123",
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_runs=[
                WorkflowRun(workflow_id="study_design", question="KRAS inhibitors"),
                WorkflowRun(workflow_id="evidence_brief", question="KRAS inhibitors"),
            ],
        )
        filters = ResearchRunQueryFilters(collection="KRAS Program", latest=True, limit=1)
        list_response = ResearchRunListResponse(items=[record], total=1, filters=filters)
        payload_response = ResearchRunResponse(
            target="run-123",
            path="/tmp/run-123.json",
            record=record,
            run=run,
        )

        assert list_response.model_dump(mode="json")["items"][0]["scope"] == "collection"
        assert payload_response.model_dump(mode="json")["run"]["workflow_runs"][0]["workflow_id"] == "study_design"
