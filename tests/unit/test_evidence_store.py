"""Unit tests for evidence storage."""

from pathlib import Path

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport
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
        date_results = store.filter_report_records(since="2026-03-03", until="2026-03-06", limit=10)

        assert len(workflow_results) == 1
        assert workflow_results[0]["workflow_id"] == "study_design"
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
