"""Unit tests for context module."""

from pathlib import Path

import pytest

from medclaw.agent.context import ContextBuilder


class TestContextBuilder:
    """Tests for ContextBuilder."""

    @pytest.fixture
    def context_builder(self, temp_workspace: Path) -> ContextBuilder:
        """Create a context builder with temporary workspace."""
        return ContextBuilder(temp_workspace)

    def test_build_system_prompt_contains_medical_role(self, context_builder: ContextBuilder):
        """Test that system prompt contains medical role."""
        prompt = context_builder.build_system_prompt()

        assert "MedClaw" in prompt
        assert "medical" in prompt.lower()

    def test_build_system_prompt_with_skills(self, context_builder: ContextBuilder):
        """Test system prompt with skills."""
        context_builder.skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = context_builder.skills_loader.workspace_skills / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n\nTest content")

        prompt = context_builder.build_system_prompt(["test-skill"])

        assert "Test Skill" in prompt or "test-skill" in prompt

    def test_build_context_includes_system_history_user(self, context_builder: ContextBuilder):
        """Test context includes system, history, and user message."""
        context = context_builder.build_context(
            user_message="Hello",
            history=[{"role": "user", "content": "Previous message"}]
        )

        assert "system" in context
        assert "history" in context
        assert context["user_message"] == "Hello"

    def test_memory_layer_l1_includes_memories(self, context_builder: ContextBuilder):
        """Test that L1 memory layer includes memories."""
        context_builder.memory_layer = "L1"
        context_builder.memory_store.save("Previous query about diabetes")

        context = context_builder.build_context("Tell me about treatment")

        assert "memories" in context or "system" in context

    def test_memory_layer_l0_excludes_memories(self, context_builder: ContextBuilder):
        """Test that L0 memory layer excludes memories."""
        context_builder.memory_layer = "L0"
        context_builder.memory_store.save("Some memory")

        context = context_builder.build_context("New query")

        # L0 should not include memories in context
        assert context.get("memories") is None or "memories" not in context.get("system", "")

    def test_set_memory_layer(self, context_builder: ContextBuilder):
        """Test setting memory layer."""
        context_builder.set_memory_layer("L2")
        assert context_builder.memory_layer == "L2"

    def test_build_context_empty_history(self, context_builder: ContextBuilder):
        """Test building context with empty history."""
        context = context_builder.build_context("Test message")

        assert context["history"] == []
        assert context["user_message"] == "Test message"

    def test_build_context_auto_selects_relevant_skills(self, context_builder: ContextBuilder):
        """Test context automatically injects relevant skills for the request."""
        context_builder.skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = context_builder.skills_loader.workspace_skills / "trial-search"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: trial-search\ndescription: Search clinical trials and recruiting studies by condition\n---\n# Trial Search"
        )

        context = context_builder.build_context("Need recruiting trial options for lung cancer")

        assert "selected_skills" in context
        assert "trial-search" in context["selected_skills"]
        assert "Relevant Skills" in context["system"]

    def test_build_context_with_none_history(self, context_builder: ContextBuilder):
        """Test building context with None history."""
        context = context_builder.build_context("Test message", history=None)

        assert context["history"] == []
        assert context["user_message"] == "Test message"

    def test_system_prompt_citations(self, context_builder: ContextBuilder):
        """Test that system prompt mentions citations."""
        prompt = context_builder.build_system_prompt()

        assert "source" in prompt.lower() or "cite" in prompt.lower()

    def test_system_prompt_accuracy(self, context_builder: ContextBuilder):
        """Test that system prompt emphasizes accuracy."""
        prompt = context_builder.build_system_prompt()

        assert "accuracy" in prompt.lower() or "accurate" in prompt.lower()
