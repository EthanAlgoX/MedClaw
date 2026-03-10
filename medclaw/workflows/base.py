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
    async def run(self, query: str, provider: LLMProvider) -> ResearchReport:
        """Execute the workflow."""

    async def synthesize(
        self,
        query: str,
        provider: LLMProvider,
        evidence: Iterable[EvidenceItem],
        instruction: str,
    ) -> str:
        """Use the configured model to summarize normalized evidence."""
        evidence_lines = []
        for item in list(evidence)[:8]:
            evidence_lines.append(
                f"- {item.title} [{item.source}] :: {item.summary or 'No summary'}"
            )
        evidence_block = "\n".join(evidence_lines) or "- No structured evidence retrieved"

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
