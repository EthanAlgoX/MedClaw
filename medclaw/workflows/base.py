"""Shared workflow primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from medclaw.evidence.models import EvidenceItem, ResearchReport
from medclaw.providers.base import LLMProvider


class ResearchWorkflow(ABC):
    """A typed medical research workflow."""

    workflow_id: str
    title: str

    @abstractmethod
    async def run(self, query: str, provider: LLMProvider | None) -> ResearchReport:
        """Execute the workflow."""

    async def synthesize(
        self,
        query: str,
        provider: LLMProvider | None,
        evidence: Iterable[EvidenceItem],
        instruction: str,
    ) -> str:
        """Use the configured model to summarize normalized evidence."""
        evidence_list = list(evidence)[:8]
        evidence_lines = []
        for item in evidence_list:
            evidence_lines.append(
                f"- {item.title} [{item.source}] :: {item.summary or 'No summary'}"
            )
        evidence_block = "\n".join(evidence_lines) or "- No structured evidence retrieved"

        if provider is None:
            return self._fallback_summary(query=query, evidence=evidence_list)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are MedClaw, a medical research assistant. Write concise, evidence-aware "
                    "summaries. Do not present the output as direct medical advice."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {query}\n\n"
                    f"Instruction: {instruction}\n\n"
                    f"Structured evidence:\n{evidence_block}"
                ),
            },
        ]
        return await provider.chat(messages, temperature=0.1, max_tokens=900)

    def _fallback_summary(self, query: str, evidence: list[EvidenceItem]) -> str:
        """Generate a deterministic summary when LLM use is disabled."""
        if not evidence:
            return (
                f"Structured workflow completed for '{query}', but no external evidence "
                "items were retrieved. Review the query, add richer sources, or rerun with an LLM."
            )

        sources = sorted({item.source for item in evidence})
        top_titles = ", ".join(item.title for item in evidence[:3])
        return (
            f"Structured workflow completed for '{query}'. Retrieved {len(evidence)} evidence "
            f"items from {', '.join(sources)}. Leading items: {top_titles}. "
            "This fallback summary was generated without an LLM."
        )
