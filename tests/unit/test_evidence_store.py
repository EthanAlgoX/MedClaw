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
