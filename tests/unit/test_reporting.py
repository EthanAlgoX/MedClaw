"""Unit tests for research report rendering."""

from medclaw.evidence.models import Citation, EvidenceItem, ResearchReport
from medclaw.reporting.briefs import render_collection_report_bundle


def test_render_collection_report_bundle_summarizes_multiple_reports():
    """Collection bundle renderer should produce a synthesis-oriented markdown brief."""
    reports = [
        ResearchReport(
            workflow_id="study_design",
            question="KRAS inhibitors",
            title="Study Design Assistant: KRAS inhibitors",
            summary="Design a biomarker-enriched cohort study.",
            key_findings=[
                "No external evidence sources were retrieved for this design memo.",
            ],
            metadata={
                "collection": "KRAS Program",
                "collection_objective": "Track resistance mechanisms and biomarker evidence",
                "saved_path": "/tmp/report-1.json",
            },
        ),
        ResearchReport(
            workflow_id="evidence_brief",
            question="KRAS inhibitors",
            title="Evidence Brief: KRAS inhibitors",
            summary="Rapid brief across literature and trial signals.",
            key_findings=[
                "Retrieved 5 literature records and 3 trial records.",
            ],
            evidence=[
                EvidenceItem(
                    id="1",
                    kind="literature",
                    source="pubmed",
                    title="Paper 1",
                    citations=[Citation(source="pubmed", title="Paper 1", identifier="PMID:1")],
                )
            ],
            metadata={
                "collection": "KRAS Program",
                "collection_objective": "Track resistance mechanisms and biomarker evidence",
                "saved_path": "/tmp/report-2.json",
            },
        ),
    ]

    rendered = render_collection_report_bundle(reports)

    assert "# Collection Brief: KRAS Program" in rendered
    assert "Track resistance mechanisms and biomarker evidence" in rendered
    assert "Workflows run: study_design, evidence_brief" in rendered
    assert "Reports generated: 2" in rendered
    assert "Structured evidence items: 1" in rendered
    assert "### Evidence Brief: KRAS inhibitors" in rendered
    assert "/tmp/report-2.json" in rendered
