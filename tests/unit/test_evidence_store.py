"""Unit tests for evidence storage."""

from pathlib import Path

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport, ResearchRun, WorkflowRun
from medclaw.evidence.store import EvidenceStore


class TestEvidenceStore:
    """Tests for EvidenceStore."""

    def test_save_report_creates_json_file(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        report = ResearchReport(
            workflow_id="evidence_brief",
            question="Test question",
            title="Test report",
            summary="Summary",
        )

        path = store.save_report(report)

        assert path.exists()
        assert path.suffix == ".json"
        assert path.parent == temp_workspace / "research" / "reports"

    def test_list_reports_returns_newest_first(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report(
            ResearchReport(
                workflow_id="evidence_brief",
                question="Q1",
                title="R1",
                summary="S1",
            )
        )
        store.save_report(
            ResearchReport(
                workflow_id="study_design",
                question="Q2",
                title="R2",
                summary="S2",
            )
        )

        reports = store.list_reports()

        assert len(reports) == 2

    def test_save_and_load_run_preserves_workflow_execution_metadata(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        run = ResearchRun(
            query="KRAS inhibitors",
            collection="KRAS Program",
            workflow_runs=[
                WorkflowRun(
                    workflow_id="literature_review",
                    question="KRAS inhibitors",
                    llm_enabled=True,
                    provider_name="fake",
                    model_name="fake-model",
                    report_path="/tmp/report.json",
                    artifact_dir="/tmp/report_artifacts",
                    artifact_paths={"report": "/tmp/report.json"},
                )
            ],
            metadata={"workflow_count": 1},
        )

        path = store.save_run(run)
        loaded = store.load_run(path)

        assert path.exists()
        assert path.parent == temp_workspace / "research" / "runs"
        assert loaded.id == run.id
        assert loaded.collection == "KRAS Program"
        assert loaded.workflow_runs[0].workflow_id == "literature_review"
        assert loaded.workflow_runs[0].model_name == "fake-model"

    def test_list_run_records_supports_latest_and_filters(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        workflow_run = store.save_run(
            ResearchRun(
                id="workflow-run",
                query="KRAS inhibitors",
                collection="KRAS Program",
                started_at="2026-03-08T09:00:00+00:00",
                completed_at="2026-03-08T09:01:00+00:00",
                workflow_runs=[
                    WorkflowRun(
                        workflow_id="literature_review",
                        question="KRAS inhibitors",
                    )
                ],
            )
        )
        store.save_run(
            ResearchRun(
                id="collection-run",
                query="EGFR biomarkers",
                collection="EGFR Program",
                started_at="2026-03-09T09:00:00+00:00",
                completed_at="2026-03-09T09:05:00+00:00",
                workflow_runs=[
                    WorkflowRun(workflow_id="study_design", question="EGFR biomarkers"),
                    WorkflowRun(workflow_id="evidence_brief", question="EGFR biomarkers"),
                ],
                metadata={"bundle_saved_path": "/tmp/bundle_summary.md"},
            )
        )

        latest_records = store.list_run_records(latest=True)
        workflow_records = store.list_run_records(workflow_id="literature_review")
        collection_records = store.list_run_records(collection="EGFR Program")
        resolved = store.get_run_record_model("workflow-run")

        assert latest_records[0]["id"] == "collection-run"
        assert latest_records[0]["scope"] == "collection"
        assert workflow_records[0]["id"] == "workflow-run"
        assert collection_records[0]["workflow_count"] == 2
        assert resolved.id == "workflow-run"
        assert resolved.path == str(workflow_run)

    def test_list_timeline_records_merges_reports_bundles_and_runs(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS inhibitors",
                title="KRAS Review",
                summary="Summary",
                generated_at="2026-03-08T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        store.save_run(
            ResearchRun(
                id="run-123",
                query="KRAS inhibitors",
                collection="KRAS Program",
                started_at="2026-03-08T09:06:00+00:00",
                completed_at="2026-03-08T09:06:00+00:00",
                workflow_runs=[
                    WorkflowRun(workflow_id="study_design", question="KRAS inhibitors"),
                    WorkflowRun(workflow_id="evidence_brief", question="KRAS inhibitors"),
                ],
            )
        )

        records = store.list_timeline_records(collection="KRAS Program", limit=10)
        typed_records = store.list_timeline_record_models(collection="KRAS Program", workflow_id="study_design", limit=10)

        assert [record["kind"] for record in records[:3]] == ["collection_bundle", "research_run", "report"]
        assert all(record["collection"] == "KRAS Program" for record in records)
        assert len(typed_records) == 1
        assert typed_records[0].kind == "research_run"
        assert typed_records[0].workflow_ids == ["study_design", "evidence_brief"]

    def test_get_collection_dashboard_model_aggregates_latest_assets(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_collection_manifest(
            name="KRAS Program",
            objective="Track KRAS evidence",
            owner="Translational Team",
            preferred_workflows=["literature_review", "evidence_brief"],
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS inhibitors",
                title="KRAS Review",
                summary="Summary",
                generated_at="2026-03-08T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="literature_review",
                    question="KRAS inhibitors",
                    title="KRAS Review",
                    summary="Summary",
                    generated_at="2026-03-08T09:05:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )
        store.save_run(
            ResearchRun(
                id="run-123",
                query="KRAS inhibitors",
                collection="KRAS Program",
                started_at="2026-03-08T09:06:00+00:00",
                completed_at="2026-03-08T09:06:00+00:00",
                workflow_runs=[
                    WorkflowRun(workflow_id="literature_review", question="KRAS inhibitors"),
                ],
            )
        )

        dashboard = store.get_collection_dashboard_model("KRAS Program", timeline_limit=3)

        assert dashboard.collection.collection == "KRAS Program"
        assert dashboard.latest_report is not None
        assert dashboard.latest_report.kind == "report"
        assert dashboard.latest_bundle is not None
        assert dashboard.latest_bundle.kind == "collection_bundle"
        assert dashboard.latest_run is not None
        assert dashboard.latest_run.id == "run-123"
        assert dashboard.covered_workflows == ["literature_review", "study_design"]
        assert dashboard.missing_preferred_workflows == ["evidence_brief"]
        assert len(dashboard.timeline) == 3

    def test_save_report_artifacts_writes_companion_files(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        report = ResearchReport(
            workflow_id="literature_review",
            question="KRAS inhibitors",
            title="Literature Review: KRAS inhibitors",
            summary="Summary",
            evidence=[
                EvidenceItem(
                    id="1",
                    kind="literature",
                    source="pubmed",
                    title="Paper 1",
                    citations=[
                        Citation(
                            source="pubmed",
                            title="Paper 1",
                            identifier="PMID:1",
                            url="https://pubmed.ncbi.nlm.nih.gov/1/",
                        )
                    ],
                )
            ],
        )

        artifact_paths = store.save_report_artifacts(report)

        assert artifact_paths["report"].exists()
        assert artifact_paths["artifact_dir"].is_dir()
        assert artifact_paths["evidence"].exists()
        assert artifact_paths["citations"].exists()
        assert artifact_paths["metadata"].exists()

    def test_list_and_search_report_records_return_compact_index(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS inhibitor resistance",
                title="KRAS Resistance Review",
                summary="Summary about resistance patterns in KRAS inhibitor treatment.",
            )
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="study_design",
                question="Adaptive oncology trial design",
                title="Adaptive Trial Design",
                summary="Summary",
            )
        )

        records = store.list_report_records(limit=10)

        assert len(records) == 2
        assert records[0]["filename"].endswith(".json")
        assert records[0]["artifact_dir"].endswith("_artifacts")
        assert records[0]["workflow_id"] in {"literature_review", "study_design"}
        assert records[0]["citation_count"] == 0
        assert "summary_preview" in records[0]

        search_results = store.search_report_records("kras", limit=10)

        assert len(search_results) == 1
        assert search_results[0]["title"] == "KRAS Resistance Review"

    def test_filter_report_records_supports_workflow_and_date_ranges(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS inhibitor resistance",
                title="KRAS Resistance Review",
                summary="Summary",
                generated_at="2026-03-01T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="study_design",
                question="Adaptive oncology trial design",
                title="Adaptive Trial Design",
                summary="Summary",
                generated_at="2026-03-05T09:00:00+00:00",
            )
        )

        workflow_results = store.filter_report_records(workflow_id="study_design", limit=10)
        collection_results = store.filter_report_records(collection="KRAS Program", limit=10)
        date_results = store.filter_report_records(since="2026-03-03", until="2026-03-06", limit=10)

        assert len(workflow_results) == 1
        assert workflow_results[0]["workflow_id"] == "study_design"
        assert len(collection_results) == 1
        assert collection_results[0]["collection"] == "KRAS Program"
        assert len(date_results) == 1
        assert date_results[0]["title"] == "Adaptive Trial Design"

    def test_filter_report_records_rejects_invalid_date(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)

        try:
            store.filter_report_records(since="2026/03/01")
        except ValueError as exc:
            assert "Invalid isoformat string" in str(exc)
        else:
            raise AssertionError("Expected ValueError for invalid date")

    def test_list_collection_records_aggregates_named_projects(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_collection_manifest(
            name="KRAS Program",
            objective="Track resistance and biomarkers",
            disease_area="Oncology",
            owner="Translational Team",
            tags=["kras", "oncology"],
            preferred_workflows=["literature_review", "evidence_brief"],
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="literature_review",
                question="KRAS inhibitor resistance",
                title="KRAS Resistance Review",
                summary="Summary",
                generated_at="2026-03-01T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="evidence_brief",
                question="KRAS biomarkers",
                title="KRAS Biomarker Brief",
                summary="Summary",
                generated_at="2026-03-06T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )

        collections = store.list_collection_records(limit=10)

        assert len(collections) == 1
        assert collections[0]["collection"] == "KRAS Program"
        assert collections[0]["report_count"] == 2
        assert collections[0]["owner"] == "Translational Team"
        assert collections[0]["latest_bundle_markdown_path"].endswith("bundle_summary.md")
        assert set(collections[0]["workflows"]) == {"literature_review", "evidence_brief"}

    def test_collection_manifest_round_trip_preserves_metadata(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)

        manifest = store.save_collection_manifest(
            name="EGFR Program",
            objective="Track EGFR biomarker evidence",
            disease_area="Thoracic oncology",
            owner="Biomarker Team",
            tags=["egfr", "nsclc", "biomarker", "egfr"],
            preferred_workflows=["evidence_brief", "literature_review", "evidence_brief"],
        )
        loaded = store.load_collection_manifest("EGFR Program")

        assert manifest["slug"] == "egfr-program"
        assert loaded["objective"] == "Track EGFR biomarker evidence"
        assert loaded["owner"] == "Biomarker Team"
        assert loaded["tags"] == ["egfr", "nsclc", "biomarker"]
        assert loaded["preferred_workflows"] == ["evidence_brief", "literature_review"]

    def test_read_artifact_returns_structured_payloads(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        report = ResearchReport(
            workflow_id="evidence_brief",
            question="EGFR biomarkers",
            title="EGFR Biomarker Brief",
            summary="Summary",
            evidence=[
                EvidenceItem(
                    id="pmid-1",
                    kind="literature",
                    source="pubmed",
                    title="Biomarker paper",
                    citations=[
                        Citation(
                            source="pubmed",
                            title="Biomarker paper",
                            identifier="PMID:1",
                            url="https://pubmed.ncbi.nlm.nih.gov/1/",
                        )
                    ],
                    metadata={"year": 2024},
                )
            ],
            metadata={"saved_by": "test"},
        )

        artifact_paths = store.save_report_artifacts(report)
        report_payload = store.read_artifact(artifact_paths["report"].name, artifact="report")
        evidence_payload = store.read_artifact(artifact_paths["report"], artifact="evidence")
        metadata_payload = store.read_artifact(artifact_paths["report"], artifact="metadata")

        assert report_payload["workflow_id"] == "evidence_brief"
        assert evidence_payload[0]["title"] == "Biomarker paper"
        assert metadata_payload["metadata"]["saved_by"] == "test"

    def test_read_artifact_rejects_unknown_artifact_type(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        path = store.save_report(
            ResearchReport(
                workflow_id="evidence_brief",
                question="Q1",
                title="R1",
                summary="S1",
            )
        )

        try:
            store.read_artifact(path, artifact="raw")
        except ValueError as exc:
            assert "Unsupported artifact" in str(exc)
        else:
            raise AssertionError("Expected ValueError for unsupported artifact")

    def test_save_collection_bundle_artifacts_writes_markdown_and_json(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        reports = [
            ResearchReport(
                workflow_id="study_design",
                question="KRAS inhibitors",
                title="Study Design Assistant: KRAS inhibitors",
                summary="Summary one",
                metadata={
                    "collection": "KRAS Program",
                    "collection_objective": "Track resistance mechanisms",
                    "saved_path": "/tmp/report-1.json",
                },
            ),
            ResearchReport(
                workflow_id="evidence_brief",
                question="KRAS inhibitors",
                title="Evidence Brief: KRAS inhibitors",
                summary="Summary two",
                metadata={
                    "collection": "KRAS Program",
                    "collection_objective": "Track resistance mechanisms",
                    "saved_path": "/tmp/report-2.json",
                },
            ),
        ]

        artifact_paths = store.save_collection_bundle_artifacts(
            reports=reports,
            markdown_summary="# Collection Brief: KRAS Program",
        )
        bundle_records = store.list_collection_bundle_records(limit=10)

        assert artifact_paths["bundle_markdown"].exists()
        assert artifact_paths["bundle_json"].exists()
        assert artifact_paths["metadata"].exists()
        assert bundle_records[0]["kind"] == "collection_bundle"
        assert bundle_records[0]["collection"] == "KRAS Program"
        assert bundle_records[0]["bundle_markdown_path"].endswith("bundle_summary.md")

    def test_list_artifact_records_combines_reports_and_bundles(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        report_path = store.save_report_artifacts(
            ResearchReport(
                workflow_id="evidence_brief",
                question="KRAS biomarkers",
                title="KRAS Biomarker Brief",
                summary="Summary",
                generated_at="2026-03-06T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )["report"]
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )

        records = store.list_artifact_records(collection="KRAS Program", limit=10)

        assert len(records) == 2
        assert {record["kind"] for record in records} == {"report", "collection_bundle"}
        assert any(record["id"] == report_path.name for record in records)
        assert any(record["id"] == bundle_paths["artifact_dir"].name for record in records)

    def test_list_artifact_records_can_filter_by_kind(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="evidence_brief",
                question="KRAS biomarkers",
                title="KRAS Biomarker Brief",
                summary="Summary",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )

        report_records = store.list_artifact_records(kind="report", limit=10)
        bundle_records = store.list_artifact_records(kind="bundle", limit=10)

        assert len(report_records) == 1
        assert report_records[0]["kind"] == "report"
        assert len(bundle_records) == 1
        assert bundle_records[0]["kind"] == "collection_bundle"

    def test_list_artifact_records_supports_latest_and_latest_by_collection(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="evidence_brief",
                question="KRAS biomarkers",
                title="KRAS Biomarker Brief",
                summary="Summary",
                generated_at="2026-03-06T09:00:00+00:00",
                metadata={"collection": "KRAS Program"},
            )
        )
        store.save_report_artifacts(
            ResearchReport(
                workflow_id="study_design",
                question="EGFR biomarkers",
                title="EGFR Study Design",
                summary="Summary",
                generated_at="2026-03-07T09:00:00+00:00",
                metadata={"collection": "EGFR Program"},
            )
        )
        store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    generated_at="2026-03-08T09:00:00+00:00",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )

        latest_record = store.list_artifact_records(latest=True, limit=10)
        latest_by_collection = store.list_artifact_records(latest_by_collection=True, limit=10)

        assert len(latest_record) == 1
        assert latest_record[0]["kind"] == "collection_bundle"
        assert len(latest_by_collection) == 2
        assert {record["collection"] for record in latest_by_collection} == {"KRAS Program", "EGFR Program"}
        assert any(record["kind"] == "collection_bundle" for record in latest_by_collection)

    def test_read_bundle_artifact_supports_markdown_and_json(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        bundle_paths = store.save_collection_bundle_artifacts(
            reports=[
                ResearchReport(
                    workflow_id="study_design",
                    question="KRAS inhibitors",
                    title="Study Design Assistant: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
                ResearchReport(
                    workflow_id="evidence_brief",
                    question="KRAS inhibitors",
                    title="Evidence Brief: KRAS inhibitors",
                    summary="Summary",
                    metadata={"collection": "KRAS Program"},
                ),
            ],
            markdown_summary="# Collection Brief: KRAS Program",
        )

        markdown_payload = store.read_bundle_artifact(bundle_paths["artifact_dir"].name, artifact="bundle_markdown")
        json_payload = store.read_bundle_artifact(bundle_paths["artifact_dir"], artifact="bundle-json")

        assert markdown_payload.startswith("# Collection Brief: KRAS Program")
        assert json_payload["kind"] == "collection_bundle"
        assert json_payload["collection"] == "KRAS Program"

    def test_store_can_return_typed_artifact_and_collection_models(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_collection_manifest(
            name="EGFR Program",
            objective="Track EGFR biomarker evidence",
            disease_area="Thoracic oncology",
            owner="Biomarker Team",
            tags=["egfr"],
            preferred_workflows=["evidence_brief"],
        )
        report = ResearchReport(
            workflow_id="evidence_brief",
            question="EGFR biomarkers",
            title="EGFR Biomarker Brief",
            summary="Summary",
            metadata={"collection": "EGFR Program"},
        )
        artifact_paths = store.save_report_artifacts(report)

        artifact_record = store.get_artifact_record_model(artifact_paths["report"].name)
        artifact_records = store.list_artifact_record_models(kind="report", limit=10)
        collection_manifest = store.load_collection_manifest_model("EGFR Program")
        collection_records = store.list_collection_record_models(limit=10)

        assert artifact_record.kind == "report"
        assert artifact_records[0].workflow_id == "evidence_brief"
        assert collection_manifest.slug == "egfr-program"
        assert collection_records[0].collection == "EGFR Program"

    def test_get_collection_record_model_supports_manifest_without_reports(self, temp_workspace: Path):
        store = EvidenceStore(temp_workspace)
        store.save_collection_manifest(
            name="KRAS Program",
            objective="Track KRAS evidence",
            disease_area="Oncology",
            owner="Translational Team",
            tags=["kras"],
            preferred_workflows=["literature_review"],
        )

        record = store.get_collection_record_model("KRAS Program")

        assert record.collection == "KRAS Program"
        assert record.report_count == 0
        assert record.preferred_workflows == ["literature_review"]
