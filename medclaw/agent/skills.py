"""Skills loader for agent capabilities."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import httpx


BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"
_EXTERNAL_CATALOG_CACHE_TTL_S = 60 * 60 * 6


class SkillsLoader:
    """Loader for agent skills.

    Skills are markdown files (SKILL.md) that teach the agent how to use
    specific tools or perform certain medical tasks.
    """

    _external_catalog_cache: tuple[float, list[dict[str, str]]] | None = None

    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None):
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR

    def list_skills(
        self,
        filter_unavailable: bool = True,
        available_tools: set[str] | None = None
    ) -> list[dict[str, str]]:
        """List all available skills."""
        skills = []

        if self.workspace_skills.exists():
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skills.append({
                            "name": skill_dir.name,
                            "path": str(skill_file),
                            "source": "workspace"
                        })

        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists() and not any(
                        s["name"] == skill_dir.name for s in skills
                    ):
                        skills.append({
                            "name": skill_dir.name,
                            "path": str(skill_file),
                            "source": "builtin"
                        })

        if filter_unavailable:
            return [
                s for s in skills
                if self._has_required_tools(
                    self.get_skill_capabilities(s["name"]),
                    available_tools
                )
            ]
        return skills

    def load_skill(self, name: str) -> str | None:
        """Load a skill by name."""
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill.read_text(encoding="utf-8")

        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill.read_text(encoding="utf-8")

        return None

    def load_skills_for_context(self, skill_names: list[str]) -> str:
        """Load specific skills for inclusion in agent context."""
        parts = []
        for name in skill_names:
            content = self.load_skill(name)
            if content:
                content = self._strip_frontmatter(content)
                parts.append(f"### Skill: {name}\n\n{content}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def build_skills_summary(
        self,
        available_tools: set[str] | None = None
    ) -> str:
        """Build a summary of all skills."""
        all_skills = self.list_skills(
            filter_unavailable=False,
            available_tools=available_tools
        )
        if not all_skills:
            return ""

        def escape_xml(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines = ["<skills>"]
        for s in all_skills:
            name = escape_xml(s["name"])
            path = s["path"]
            desc = escape_xml(self._get_skill_description(s["name"]))
            capabilities = self.get_skill_capabilities(s["name"])

            lines.append(f'  <skill available="true">')
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"    <location>{path}</location>")

            if capabilities.get("triggers"):
                lines.append(
                    f"    <triggers>{escape_xml(', '.join(capabilities['triggers']))}</triggers>"
                )
            if capabilities.get("tools"):
                lines.append(
                    f"    <tools>{escape_xml(', '.join(capabilities['tools']))}</tools>"
                )

            lines.append("  </skill>")

        lines.append("</skills>")
        return "\n".join(lines)

    def _get_skill_description(self, name: str) -> str:
        """Get the description of a skill from its frontmatter."""
        meta = self.get_skill_metadata(name)
        if meta and meta.get("description"):
            return meta["description"]
        return name

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from markdown content."""
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end():].strip()
        return content

    def _parse_medclaw_metadata(self, raw: str) -> dict:
        """Parse skill metadata from frontmatter."""
        if isinstance(raw, dict):
            return raw.get("medclaw", raw) if isinstance(raw, dict) else {}
        try:
            data = json.loads(raw)
            return data.get("medclaw", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_skill_capabilities(self, name: str) -> dict:
        """Get normalized capability metadata used for routing."""
        meta = self._get_skill_meta(name)
        return {
            "triggers": self._normalize_metadata_list(meta.get("triggers", [])),
            "output": meta.get("output"),
            "risk": meta.get("risk"),
            "freshness": meta.get("freshness"),
            "tools": self._normalize_metadata_list(meta.get("tools", [])),
            "required_tools": self._normalize_metadata_list(meta.get("required_tools", [])),
            "domains": self._normalize_metadata_list(meta.get("domains", [])),
        }

    def _get_skill_meta(self, name: str) -> dict:
        """Get medclaw metadata for a skill."""
        meta = self.get_skill_metadata(name) or {}
        return self._parse_medclaw_metadata(meta.get("metadata", ""))

    @staticmethod
    def _normalize_metadata_list(value: Any) -> list[str]:
        """Normalize metadata into a stable list of strings."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _has_required_tools(
        capabilities: dict,
        available_tools: set[str] | None
    ) -> bool:
        """Return True when runtime tool availability satisfies required_tools."""
        if available_tools is None:
            return True
        required = {
            str(name).strip()
            for name in capabilities.get("required_tools", [])
            if str(name).strip()
        }
        return required.issubset(available_tools)

    def match_skills_for_request(
        self,
        text: str,
        available_tools: set[str] | None = None,
    ) -> list[str]:
        """Return skills whose trigger metadata matches the given text."""
        lowered = text.lower()
        matched = []
        for item in self.list_skills(
            filter_unavailable=True,
            available_tools=available_tools
        ):
            capabilities = self.get_skill_capabilities(item["name"])
            triggers = [str(trigger).lower() for trigger in capabilities.get("triggers", [])]
            if any(trigger and trigger in lowered for trigger in triggers):
                matched.append(item["name"])
        return matched

    def search_local_skills(
        self,
        text: str,
        limit: int = 5,
        available_tools: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """Search local/workspace skills by name and description."""
        lowered = text.lower()
        tokens = {
            token
            for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", lowered)
            if len(token) >= 2
        }
        ranked = []
        for item in self.list_skills(
            filter_unavailable=False,
            available_tools=available_tools
        ):
            description = self._get_skill_description(item["name"])
            haystack = f"{item['name']} {description}".lower()
            score = 0
            if item["name"].replace("-", " ") in lowered:
                score += 8
            for token in tokens:
                if token in haystack:
                    score += 2
            if score <= 0:
                continue
            ranked.append((score, {**item, "description": description}))

        ranked.sort(key=lambda row: (-row[0], row[1]["name"]))
        return [entry for _, entry in ranked[:limit]]

    def get_skill_metadata(self, name: str) -> dict | None:
        """Get metadata from a skill's frontmatter."""
        content = self.load_skill(name)
        if not content:
            return None

        if content.startswith("---"):
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                return self._parse_frontmatter(match.group(1))

        return None

    @staticmethod
    def _parse_frontmatter(raw: str) -> dict:
        """Parse simple frontmatter with JSON-friendly values."""
        metadata = {}
        for line in raw.split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            text = value.strip()
            if not key:
                continue
            metadata[key] = SkillsLoader._parse_frontmatter_value(text)
        return metadata

    @staticmethod
    def _parse_frontmatter_value(value: str) -> Any:
        """Parse scalar or JSON-like frontmatter values."""
        if not value:
            return ""
        if value[0] in "[{":
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"

        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            pass

        return value
