"""Context builder for agent conversations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from medclaw.agent.memory import MemoryStore
from medclaw.agent.skills import SkillsLoader


class ContextBuilder:
    """Builds context for agent conversations."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_store = MemoryStore(workspace)
        self.skills_loader = SkillsLoader(workspace)
        self.memory_layer = "L1"

    def set_memory_layer(self, layer: str = "L1") -> None:
        """Set memory layer (L1, L2, L3)."""
        self.memory_layer = layer

    def build_system_prompt(self, skills: list[str] | None = None) -> str:
        """Build system prompt with skills."""
        prompt_parts = [
            "You are MedClaw, an AI-powered medical research assistant.",
            "Your role is to help medical students, clinicians, and researchers with:",
            "- Literature review and paper analysis",
            "- Clinical trial information",
            "- Drug information and interactions",
            "- Study design and statistical analysis",
            "- Medical knowledge queries",
            "",
            "Always prioritize accuracy and cite your sources.",
            "When uncertain, acknowledge limitations rather than providing potentially incorrect information.",
        ]

        if skills:
            prompt_parts.append("")
            prompt_parts.append(
                "The following skills were auto-selected for this request based on the user's topic."
            )
            skills_content = self.skills_loader.load_skills_for_context(skills)
            if skills_content:
                prompt_parts.append("\n## Relevant Skills\n")
                prompt_parts.append(skills_content)

        return "\n".join(prompt_parts)

    def build_context(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build complete context for a conversation turn."""
        selected_skills = skills or self.skills_loader.match_skills_for_request(user_message)
        context = {
            "system": self.build_system_prompt(selected_skills or None),
            "history": history or [],
            "user_message": user_message,
        }
        if selected_skills:
            context["selected_skills"] = selected_skills

        if self.memory_layer != "L0":
            relevant_memories = self.memory_store.retrieve(user_message, limit=5)
            if relevant_memories:
                context["memories"] = relevant_memories

        return context
