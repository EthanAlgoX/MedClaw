"""Unit tests for evidence storage."""

from pathlib import Path

from medclaw.evidence.models import ResearchReport
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
