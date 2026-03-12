"""Unit tests for application-layer response builders."""

from medclaw.application.responses import (
    build_artifact_list_response,
    build_artifact_payload_list_response,
    build_artifact_payload_response,
    build_artifact_query_filters,
    build_collection_dashboard_response,
    build_collection_list_response,
    build_collection_response,
    build_config_response,
    build_provider_response,
    build_provider_summary,
    build_research_run_list_response,
    build_research_run_query_filters,
    build_research_run_response,
    build_research_timeline_list_response,
    build_research_timeline_query_filters,
    build_research_report_list_response,
    build_research_report_response,
    build_skill_list_response,
    build_workspace_response,
    build_workspace_summary,
    build_workflow_list_response,
)
from medclaw.application.query_models import SkillSummary, WorkflowSummary
from medclaw.evidence.api_models import (
    CollectionDashboard,
    artifact_record_from_dict,
    collection_manifest_from_dict,
    collection_record_from_dict,
    research_run_record_from_dict,
    research_timeline_record_from_dict,
)
from medclaw.evidence.models import ResearchReport, ResearchRun, WorkflowRun


class TestApplicationResponses:
    """Tests for response builder helpers."""

    def test_build_research_report_responses(self):
        report = ResearchReport(
            workflow_id="literature_review",
            question="KRAS inhibitors",
            title="KRAS Review",
            summary="Summary",
        )

        single = build_research_report_response(report)
        many = build_research_report_list_response([report])

        assert single.model_dump(mode="json")["report"]["workflow_id"] == "literature_review"
        assert many.model_dump(mode="json")["total"] == 1

    def test_build_research_run_responses(self):
        record = research_run_record_from_dict(
            {
                "id": "run-123",
                "path": "/tmp/run-123.json",
                "filename": "20260308_run-123.json",
                "scope": "workflow",
                "query": "KRAS inhibitors",
                "collection": "",
                "status": "completed",
                "started_at": "2026-03-08T09:00:00+00:00",
                "completed_at": "2026-03-08T09:01:00+00:00",
                "workflow_count": 1,
                "workflow_ids": ["literature_review"],
                "bundle_saved_path": "",
            }
        )
        run = ResearchRun(
            id="run-123",
            query="KRAS inhibitors",
            workflow_runs=[WorkflowRun(workflow_id="literature_review", question="KRAS inhibitors")],
        )

        filters = build_research_run_query_filters(workflow_id="literature_review", latest=True, limit=1)
        list_response = build_research_run_list_response([record], filters)
        response = build_research_run_response(
            target="run-123",
            path="/tmp/run-123.json",
            record=record,
            run=run,
        )

        assert list_response.model_dump(mode="json")["items"][0]["workflow_ids"] == ["literature_review"]
        assert response.model_dump(mode="json")["record"]["id"] == "run-123"

    def test_build_research_timeline_response(self):
        record = research_timeline_record_from_dict(
            {
                "kind": "report",
                "id": "report.json",
                "path": "/tmp/report.json",
                "collection": "KRAS Program",
                "timestamp": "2026-03-08T09:00:00+00:00",
                "title": "KRAS Review",
                "query": "KRAS inhibitors",
                "workflow_ids": ["literature_review"],
                "scope": "workflow",
                "summary_preview": "Summary",
            }
        )

        filters = build_research_timeline_query_filters(collection="KRAS Program", limit=10)
        response = build_research_timeline_list_response([record], filters)

        assert response.model_dump(mode="json")["items"][0]["title"] == "KRAS Review"
        assert response.model_dump(mode="json")["filters"]["collection"] == "KRAS Program"

    def test_build_collection_dashboard_response(self):
        dashboard = CollectionDashboard(
            collection=collection_record_from_dict(
                {
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
                }
            ),
            covered_workflows=["literature_review"],
            missing_preferred_workflows=["evidence_brief"],
            latest_activity_at="2026-03-08T09:00:00+00:00",
            stale=False,
            stale_days=5,
            health_signals=["missing_preferred_workflow:evidence_brief"],
        )

        response = build_collection_dashboard_response(dashboard)

        assert response.model_dump(mode="json")["item"]["collection"]["collection"] == "KRAS Program"
        assert response.model_dump(mode="json")["item"]["stale"] is False

    def test_build_artifact_responses(self):
        filters = build_artifact_query_filters(kind="report", latest=True, limit=1)
        record = artifact_record_from_dict(
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
            "evidence_count": 1,
            "citation_count": 1,
            "summary_preview": "Summary",
            "artifact_dir": "/tmp/report_artifacts",
            }
        )
        payload = [
            {
                "source": "pubmed",
                "title": "KRAS paper",
                "identifier": "PMID:1",
            }
        ]

        artifact_list = build_artifact_list_response([record], filters)
        artifact_payload = build_artifact_payload_response(
            target="report.json",
            artifact="citations",
            record=record,
            path="/tmp/report_artifacts/citations.json",
            payload=payload,
        )
        artifact_payload_list = build_artifact_payload_list_response([artifact_payload], filters=filters)

        assert artifact_list.model_dump(mode="json")["items"][0]["kind"] == "report"
        assert artifact_payload.model_dump(mode="json")["payload"][0]["identifier"] == "PMID:1"
        assert artifact_payload_list.model_dump(mode="json")["total"] == 1

    def test_build_collection_responses(self):
        manifest = collection_manifest_from_dict(
            {
            "name": "EGFR Program",
            "slug": "egfr-program",
            "objective": "Track EGFR biomarker evidence",
            "disease_area": "Thoracic oncology",
            "owner": "Biomarker Team",
            "tags": ["egfr"],
            "preferred_workflows": ["evidence_brief"],
            "created_at": "",
            "updated_at": "",
            }
        )
        record = collection_record_from_dict(
            {
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

        collection_manifest = build_collection_response(manifest)
        collection_record = build_collection_response(record)
        collection_list = build_collection_list_response([record], limit=20)

        assert collection_manifest.model_dump(mode="json")["item"]["slug"] == "egfr-program"
        assert collection_record.model_dump(mode="json")["item"]["report_count"] == 1
        assert collection_list.model_dump(mode="json")["items"][0]["collection"] == "EGFR Program"
        assert collection_list.model_dump(mode="json")["items"][0]["health_signals"] == ["no_run"]

    def test_build_workflow_and_skill_list_responses(self):
        workflows = [WorkflowSummary(id="literature_review", title="Literature Review")]
        skills = [
            SkillSummary(
                name="pubmed-search",
                path="/tmp/pubmed-search/SKILL.md",
                source="builtin",
                description="Search PubMed",
                relevance_score="15.0",
                reasons="exact name match",
            )
        ]

        workflow_response = build_workflow_list_response(workflows)
        skill_response = build_skill_list_response(skills, query="pubmed")

        assert workflow_response.model_dump(mode="json")["items"][0]["id"] == "literature_review"
        assert skill_response.model_dump(mode="json")["items"][0]["name"] == "pubmed-search"
        assert skill_response.model_dump(mode="json")["query"] == "pubmed"

    def test_build_system_responses(self):
        workspace = build_workspace_summary(
            path="/tmp/workspace",
            exists=True,
            skills_path="/tmp/workspace/skills",
            memory_path="/tmp/workspace/memory",
            reports_path="/tmp/workspace/reports",
            research_path="/tmp/workspace/research",
            collections_path="/tmp/workspace/research/collections",
        )
        provider = build_provider_summary(
            name="openrouter",
            configured=True,
            has_api_key=True,
            base_url="https://openrouter.ai/api/v1",
            is_default=True,
        )
        config = build_config_response(
            config_path="/tmp/config.json",
            workspace=workspace,
            default_provider="openrouter",
            default_model="anthropic/claude-sonnet-4-20250514",
            temperature=0.1,
            max_tokens=4096,
            providers=[provider],
        )
        provider_response = build_provider_response(provider)
        workspace_response = build_workspace_response(workspace)

        assert config.model_dump(mode="json")["item"]["default_provider"] == "openrouter"
        assert provider_response.model_dump(mode="json")["item"]["name"] == "openrouter"
        assert workspace_response.model_dump(mode="json")["item"]["path"] == "/tmp/workspace"
