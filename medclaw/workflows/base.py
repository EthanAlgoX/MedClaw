"""Shared workflow primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from medclaw.evidence.models import EvidenceItem, ResearchReport
from medclaw.providers.base import LLMProvider

CollectionContext = dict[str, Any]


class ResearchWorkflow(ABC):
    """A typed medical research workflow."""

    workflow_id: str
    title: str

    @abstractmethod
    async def run(
        self,
        query: str,
        provider: LLMProvider | None,
        collection_context: CollectionContext | None = None,
    ) -> ResearchReport:
        """Execute the workflow."""

    async def synthesize(
        self,
        query: str,
        provider: LLMProvider | None,
        evidence: Iterable[EvidenceItem],
        instruction: str,
        collection_context: CollectionContext | None = None,
    ) -> str:
        """Use the configured model to summarize normalized evidence."""
        evidence_list = list(evidence)[:8]
        evidence_lines = []
        for item in evidence_list:
            evidence_lines.append(
                f"- {item.title} [{item.source}] :: {item.summary or 'No summary'}"
            )
        evidence_block = "\n".join(evidence_lines) or "- No structured evidence retrieved"
        collection_block = self._collection_block(collection_context)

        if provider is None:
            return self._fallback_summary(
                query=query,
                evidence=evidence_list,
                collection_context=collection_context,
            )

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
                    f"Instruction: {self._compose_instruction(instruction, collection_context)}\n\n"
                    f"{collection_block}"
                    f"Structured evidence:\n{evidence_block}"
                ),
            },
        ]
        return await provider.chat(messages, temperature=0.1, max_tokens=900)

    def build_report_metadata(
        self,
        collection_context: CollectionContext | None = None,
    ) -> dict[str, Any]:
        """Build structured metadata shared across workflow reports."""
        if not collection_context:
            return {}
        metadata = {
            "collection": collection_context.get("name", ""),
            "collection_slug": collection_context.get("slug", ""),
            "collection_objective": collection_context.get("objective", ""),
            "collection_disease_area": collection_context.get("disease_area", ""),
            "collection_owner": collection_context.get("owner", ""),
            "collection_tags": collection_context.get("tags", []),
            "collection_preferred_workflows": collection_context.get("preferred_workflows", []),
        }
        return {key: value for key, value in metadata.items() if value not in ("", [], None)}

    def _fallback_summary(
        self,
        query: str,
        evidence: list[EvidenceItem],
        collection_context: CollectionContext | None = None,
    ) -> str:
        """Generate a deterministic summary when LLM use is disabled."""
        collection_phrase = self._collection_fallback_phrase(collection_context)
        if not evidence:
            return (
                f"Structured workflow completed for '{query}'{collection_phrase}, but no external "
                "evidence items were retrieved. Review the query, add richer sources, or rerun with an LLM."
            )

        sources = sorted({item.source for item in evidence})
        top_titles = ", ".join(item.title for item in evidence[:3])
        return (
            f"Structured workflow completed for '{query}'{collection_phrase}. Retrieved {len(evidence)} evidence "
            f"items from {', '.join(sources)}. Leading items: {top_titles}. "
            "This fallback summary was generated without an LLM."
        )

    def _compose_instruction(
        self,
        instruction: str,
        collection_context: CollectionContext | None,
    ) -> str:
        """Augment workflow instructions with collection-level research context."""
        if not collection_context:
            return instruction

        additions = []
        if collection_context.get("objective"):
            additions.append(f"Align the summary to this collection objective: {collection_context['objective']}.")
        if collection_context.get("preferred_workflows"):
            additions.append(
                "Keep the output compatible with these preferred workflows: "
                f"{', '.join(collection_context['preferred_workflows'])}."
            )
        if collection_context.get("tags"):
            additions.append(
                f"Preserve these program tags where relevant: {', '.join(collection_context['tags'])}."
            )
        if not additions:
            return instruction
        return f"{instruction} {' '.join(additions)}"

    def _collection_block(self, collection_context: CollectionContext | None) -> str:
        """Serialize collection context for prompt injection."""
        if not collection_context:
            return ""

        lines = [f"Collection: {collection_context.get('name', '')}"]
        if collection_context.get("objective"):
            lines.append(f"Objective: {collection_context['objective']}")
        if collection_context.get("disease_area"):
            lines.append(f"Disease area: {collection_context['disease_area']}")
        if collection_context.get("owner"):
            lines.append(f"Owner: {collection_context['owner']}")
        if collection_context.get("tags"):
            lines.append(f"Tags: {', '.join(collection_context['tags'])}")
        if collection_context.get("preferred_workflows"):
            lines.append(
                "Preferred workflows: "
                + ", ".join(collection_context["preferred_workflows"])
            )
        return "\n".join(lines) + "\n\n"

    def _collection_fallback_phrase(
        self,
        collection_context: CollectionContext | None,
    ) -> str:
        """Return a compact phrase describing collection context for fallback summaries."""
        if not collection_context:
            return ""

        collection_name = collection_context.get("name", "").strip()
        objective = collection_context.get("objective", "").strip()
        if collection_name and objective:
            return f" for collection '{collection_name}' (objective: {objective})"
        if collection_name:
            return f" for collection '{collection_name}'"
        return ""
