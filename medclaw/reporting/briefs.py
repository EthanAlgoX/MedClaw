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
