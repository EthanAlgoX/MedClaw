"""Render structured research reports into user-facing markdown."""

from __future__ import annotations

from medclaw.evidence.models import ResearchReport


def render_research_report(report: ResearchReport) -> str:
    """Render a research report as compact markdown."""
    lines = [f"# {report.title}", "", report.summary.strip() or "No summary available."]

    if report.key_findings:
        lines.extend(["", "## Key Findings"])
        lines.extend(f"- {finding}" for finding in report.key_findings)

    if report.evidence:
        lines.extend(["", "## Evidence"])
        for item in report.evidence[:8]:
            lines.append(f"- **{item.title}** ({item.source})")
            if item.summary:
                lines.append(f"  - {item.summary}")
            if item.citations:
                citation = item.citations[0]
                cite_bits = [citation.source]
                if citation.identifier:
                    cite_bits.append(citation.identifier)
                if citation.url:
                    cite_bits.append(citation.url)
                lines.append(f"  - Citation: {' | '.join(cite_bits)}")

    if report.disclaimer:
        lines.extend(["", "## Disclaimer", report.disclaimer])

    return "\n".join(lines).strip()


def render_collection_report_bundle(reports: list[ResearchReport]) -> str:
    """Render a collection-level synthesis brief across multiple workflow reports."""
    if not reports:
        return "# Research Bundle\n\nNo reports available."

    first_report = reports[0]
    collection = first_report.metadata.get("collection", "").strip()
    collection_objective = first_report.metadata.get("collection_objective", "").strip()
    title = (
        f"# Collection Brief: {collection}"
        if collection
        else "# Research Workflow Bundle"
    )

    workflows = [report.workflow_id for report in reports]
    total_evidence = sum(len(report.evidence) for report in reports)
    total_citations = sum(
        sum(len(item.citations) for item in report.evidence)
        for report in reports
    )

    lines = [title]
    if collection_objective:
        lines.extend(["", collection_objective])

    lines.extend(
        [
            "",
            "## Program Snapshot",
            f"- Workflows run: {', '.join(workflows)}",
            f"- Reports generated: {len(reports)}",
            f"- Structured evidence items: {total_evidence}",
            f"- Citation mentions: {total_citations}",
        ]
    )

    lines.extend(["", "## Cross-Workflow Synthesis"])
    for report in reports:
        finding = report.key_findings[0] if report.key_findings else report.summary.strip()
        lines.append(f"- **{report.title}**: {finding}")

    lines.extend(["", "## Workflow Reports"])
    for report in reports:
        lines.extend(
            [
                "",
                f"### {report.title}",
                report.summary.strip() or "No summary available.",
            ]
        )
        if report.key_findings:
            lines.append("")
            lines.extend(f"- {finding}" for finding in report.key_findings[:3])
        saved_path = report.metadata.get("saved_path", "")
        if saved_path:
            lines.append(f"- Saved report: {saved_path}")

    return "\n".join(lines).strip()
