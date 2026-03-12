"""Unit tests for typed artifact API models."""

from medclaw.evidence.api_models import (
    ArtifactListResponse,
    ArtifactPayloadResponse,
    ArtifactQueryFilters,
    CollectionDashboardListResponse,
    CollectionDashboardQueryFilters,
    CollectionDashboardResponse,
    CollectionListResponse,
    CollectionResponse,
    ResearchRunListResponse,
    ResearchRunQueryFilters,
    ResearchRunResponse,
    ResearchTimelineListResponse,
    ResearchTimelineQueryFilters,
    ResearchReportListResponse,
    ResearchReportResponse,
    artifact_record_from_dict,
    research_run_record_from_dict,
    research_timeline_record_from_dict,
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
                "latest_run_id": "",
                "latest_run_completed_at": "",
                "latest_activity_at": "2026-03-08T09:00:00+00:00",
                "stale": False,
                "stale_days": 5,
                "health_signals": ["no_run"],
                "missing_preferred_workflows": [],
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

    def test_research_timeline_response_models_dump_envelopes(self):
        record = research_timeline_record_from_dict(
            {
                "kind": "research_run",
                "id": "run-123",
                "path": "/tmp/run-123.json",
                "collection": "KRAS Program",
                "timestamp": "2026-03-08T09:10:00+00:00",
                "title": "Research Run: run-123",
                "query": "KRAS inhibitors",
                "workflow_ids": ["study_design", "evidence_brief"],
                "scope": "collection",
                "summary_preview": "",
            }
        )
        filters = ResearchTimelineQueryFilters(collection="KRAS Program", limit=10)
        response = ResearchTimelineListResponse(items=[record], total=1, filters=filters)

        assert response.model_dump(mode="json")["items"][0]["kind"] == "research_run"
        assert response.model_dump(mode="json")["filters"]["collection"] == "KRAS Program"

    def test_collection_dashboard_response_models_dump_envelopes(self):
        response = CollectionDashboardResponse(
            item={
                "collection": {
                    "collection": "KRAS Program",
                    "slug": "kras-program",
                    "objective": "Track KRAS evidence",
                    "disease_area": "Oncology",
                    "owner": "Translational Team",
                    "tags": ["kras"],
                    "preferred_workflows": ["literature_review", "evidence_brief"],
                    "created_at": "",
                    "updated_at": "",
                    "report_count": 1,
                    "evidence_count": 2,
                    "citation_count": 2,
                    "latest_generated_at": "2026-03-08T09:00:00+00:00",
                    "latest_bundle_generated_at": "",
                    "latest_bundle_markdown_path": "",
                    "latest_bundle_json_path": "",
                    "workflows": ["literature_review"],
                    "titles": ["KRAS Review"],
                },
                "latest_report": None,
                "latest_bundle": None,
                "latest_run": None,
                "timeline": [],
                "covered_workflows": ["literature_review"],
                "missing_preferred_workflows": ["evidence_brief"],
                "latest_activity_at": "2026-03-08T09:00:00+00:00",
                "stale": False,
                "stale_days": 5,
                "health_signals": ["missing_preferred_workflow:evidence_brief"],
            }
        )

        assert response.model_dump(mode="json")["item"]["collection"]["slug"] == "kras-program"
        assert response.model_dump(mode="json")["item"]["health_signals"] == [
            "missing_preferred_workflow:evidence_brief"
        ]

    def test_collection_dashboard_list_response_models_dump_envelopes(self):
        filters = CollectionDashboardQueryFilters(only_unhealthy=True, limit=5, timeline_limit=3)
        response = CollectionDashboardListResponse(
            items=[
                {
                    "collection": {
                        "collection": "Dormant Program",
                        "slug": "dormant-program",
                        "report_count": 1,
                        "workflows": ["literature_review"],
                        "titles": ["Legacy Review"],
                    },
                    "latest_report": None,
                    "latest_bundle": None,
                    "latest_run": None,
                    "timeline": [],
                    "covered_workflows": ["literature_review"],
                    "missing_preferred_workflows": [],
                    "latest_activity_at": "2025-01-01T09:00:00+00:00",
                    "stale": True,
                    "stale_days": 60,
                    "health_signals": ["stale_collection"],
                }
            ],
            total=1,
            filters=filters,
        )

        assert response.model_dump(mode="json")["items"][0]["collection"]["slug"] == "dormant-program"
        assert response.model_dump(mode="json")["filters"]["only_unhealthy"] is True
