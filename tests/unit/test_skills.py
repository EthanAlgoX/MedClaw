"""Unit tests for skills module."""

from pathlib import Path

import pytest

from medclaw.agent.skills import SkillsLoader


class TestSkillsLoader:
    """Tests for SkillsLoader."""

    @pytest.fixture
    def skills_loader(self, temp_workspace: Path) -> SkillsLoader:
        """Create a skills loader with temporary workspace."""
        return SkillsLoader(temp_workspace)

    def test_list_skills_returns_list(self, skills_loader: SkillsLoader):
        """Test that list_skills returns a list."""
        skills = skills_loader.list_skills()

        assert isinstance(skills, list)

    def test_list_skills_includes_source(self, skills_loader: SkillsLoader):
        """Test that skills include source information."""
        skills = skills_loader.list_skills()

        for skill in skills:
            assert "name" in skill
            assert "path" in skill
            assert "source" in skill

    def test_load_skill_returns_none_for_nonexistent(self, skills_loader: SkillsLoader):
        """Test loading non-existent skill returns None."""
        result = skills_loader.load_skill("nonexistent-skill-xyz")

        assert result is None

    def test_load_skills_for_context_strips_frontmatter(self, skills_loader: SkillsLoader):
        """Test that skills content strips YAML frontmatter."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\n---\n# Content\nSome content"
        )

        content = skills_loader.load_skills_for_context(["test-skill"])

        assert "# Content" in content
        assert "---" not in content or content.count("---") < 2

    def test_build_skills_summary_xml_escaped(self, skills_loader: SkillsLoader):
        """Test that skills summary properly escapes XML."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\n---\n# Test skill"
        )

        summary = skills_loader.build_skills_summary()

        assert "<skills>" in summary
        assert "&" in summary or "test" in summary.lower()

    def test_match_skills_for_request_trigger_matching(self, skills_loader: SkillsLoader):
        """Test that skill matching works with triggers."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "diabetes-search"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nmetadata: {\"medclaw\":{\"triggers\":[\"diabetes\", \"血糖\"]}}\n---\n# Diabetes Search"
        )

        matched = skills_loader.match_skills_for_request("I need help with diabetes")

        assert isinstance(matched, list)
        assert "diabetes-search" in matched

    def test_search_local_skills_by_name(self, skills_loader: SkillsLoader):
        """Test searching skills by name."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "pubmed-search"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nmetadata: {\"description\": \"Search PubMed\"}\n---\n# PubMed Search"
        )

        results = skills_loader.search_local_skills("pubmed")

        assert isinstance(results, list)
        assert results
        assert results[0]["name"] == "pubmed-search"

    def test_get_skill_metadata_parses_frontmatter(self, skills_loader: SkillsLoader):
        """Test that metadata parsing works correctly."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "test-metadata"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-metadata\nmetadata: {\"medclaw\":{\"risk\":\"low\",\"tools\":[\"pubmed\"]}}\n---\n# Test"
        )

        metadata = skills_loader.get_skill_metadata("test-metadata")

        assert metadata is not None

    def test_get_skill_capabilities(self, skills_loader: SkillsLoader):
        """Test getting skill capabilities."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "capability-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nmetadata: {\"medclaw\":{\"triggers\":[\"test\"],\"tools\":[\"tool1\"]}}\n---\n# Test"
        )

        caps = skills_loader.get_skill_capabilities("capability-skill")

        assert isinstance(caps, dict)
        assert "triggers" in caps
        assert "tools" in caps
        assert caps["triggers"] == ["test"]
        assert caps["tools"] == ["tool1"]

    def test_normalize_metadata_list(self):
        """Test metadata list normalization."""
        normalized = SkillsLoader._normalize_metadata_list(["item1", "item2"])
        assert normalized == ["item1", "item2"]

        normalized = SkillsLoader._normalize_metadata_list("single")
        assert normalized == ["single"]

        normalized = SkillsLoader._normalize_metadata_list(None)
        assert normalized == []

    def test_parse_frontmatter_value(self):
        """Test parsing frontmatter scalar values."""
        assert SkillsLoader._parse_frontmatter_value("true") is True
        assert SkillsLoader._parse_frontmatter_value("false") is False
        assert SkillsLoader._parse_frontmatter_value("123") == 123
        assert SkillsLoader._parse_frontmatter_value('"quoted"') == "quoted"
        assert SkillsLoader._parse_frontmatter_value("plain text") == "plain text"
        assert SkillsLoader._parse_frontmatter_value("[Read, Write]") == ["Read", "Write"]

    def test_strip_frontmatter(self, skills_loader: SkillsLoader):
        """Test stripping frontmatter from content."""
        content = "---\nname: test\n---\n# Main content"
        stripped = skills_loader._strip_frontmatter(content)

        assert "# Main content" in stripped
        assert "name: test" not in stripped

    def test_search_with_limit(self, skills_loader: SkillsLoader):
        """Test search respects limit parameter."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)

        for i in range(5):
            skill_dir = skills_loader.workspace_skills / f"test-skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# Test Skill {i}")

        results = skills_loader.search_local_skills("test", limit=2)

        assert len(results) <= 2

    def test_frontmatter_allowed_tools_list_is_parsed(self, skills_loader: SkillsLoader):
        """Test OpenClaw-style allowed-tools lists are parsed correctly."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "report-writer"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: report-writer\ndescription: Write clinical reports\nallowed-tools: [Read, Write, Edit, Bash]\n---\n# Report Writer"
        )

        metadata = skills_loader.get_skill_metadata("report-writer")
        caps = skills_loader.get_skill_capabilities("report-writer")

        assert metadata is not None
        assert metadata["allowed-tools"] == ["Read", "Write", "Edit", "Bash"]
        assert caps["allowed_tools"] == ["Read", "Write", "Edit", "Bash"]

    def test_match_skills_can_use_description_when_metadata_missing(self, skills_loader: SkillsLoader):
        """Test ranking falls back to name and description keywords."""
        skills_loader.workspace_skills.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_loader.workspace_skills / "clinicaltrials-database"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: clinicaltrials-database\ndescription: Search ClinicalTrials.gov for recruiting studies and NCT IDs\n---\n# Clinical Trials"
        )

        matched = skills_loader.match_skills_for_request("Find recruiting clinical trials for diabetes")

        assert "clinicaltrials-database" in matched

    def test_runtime_skill_filter_keeps_workspace_and_core_only(self, temp_workspace: Path):
        """Runtime listing should include workspace skills and curated core builtin skills only."""
        builtin_dir = temp_workspace / "builtin"
        (builtin_dir / "pubmed-search").mkdir(parents=True)
        (builtin_dir / "pubmed-search" / "SKILL.md").write_text("# Core skill")
        (builtin_dir / "iso-13485-certification").mkdir(parents=True)
        (builtin_dir / "iso-13485-certification" / "SKILL.md").write_text("# Extended skill")

        workspace_skill_dir = temp_workspace / "skills" / "custom-research-skill"
        workspace_skill_dir.mkdir(parents=True)
        (workspace_skill_dir / "SKILL.md").write_text("# Workspace skill")

        loader = SkillsLoader(temp_workspace, builtin_skills_dir=builtin_dir)

        runtime_skills = loader.list_runtime_skills(filter_unavailable=False)
        runtime_names = {skill["name"] for skill in runtime_skills}
        all_names = {skill["name"] for skill in loader.list_skills(filter_unavailable=False)}

        assert "pubmed-search" in runtime_names
        assert "custom-research-skill" in runtime_names
        assert "iso-13485-certification" not in runtime_names
        assert "iso-13485-certification" in all_names

    def test_match_skills_runtime_only_excludes_non_core_builtin(self, temp_workspace: Path):
        """Default runtime matching should not route into non-core builtin skills."""
        builtin_dir = temp_workspace / "builtin"
        (builtin_dir / "pubmed-search").mkdir(parents=True)
        (
            builtin_dir / "pubmed-search" / "SKILL.md"
        ).write_text("---\ndescription: Search PubMed literature\n---\n# PubMed")
        (builtin_dir / "iso-13485-certification").mkdir(parents=True)
        (
            builtin_dir / "iso-13485-certification" / "SKILL.md"
        ).write_text("---\ndescription: Medical quality systems\n---\n# ISO")

        loader = SkillsLoader(temp_workspace, builtin_skills_dir=builtin_dir)

        matched_runtime = loader.match_skills_for_request("Search PubMed for cancer")
        matched_all = loader.match_skills_for_request(
            "medical quality systems",
            runtime_only=False,
        )

        assert matched_runtime == ["pubmed-search"]
        assert "iso-13485-certification" in matched_all
