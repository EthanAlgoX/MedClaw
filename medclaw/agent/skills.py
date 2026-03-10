"""Skills loader for agent capabilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillsLoader:
    """Load, summarize, and rank MedClaw skills."""

    _STOPWORDS = {
        "a",
        "an",
        "and",
        "api",
        "assistant",
        "based",
        "bio",
        "case",
        "clinical",
        "data",
        "database",
        "design",
        "for",
        "from",
        "guide",
        "guidance",
        "how",
        "in",
        "integration",
        "into",
        "medical",
        "of",
        "on",
        "or",
        "pipeline",
        "report",
        "research",
        "review",
        "search",
        "skill",
        "study",
        "system",
        "the",
        "tool",
        "tools",
        "use",
        "using",
        "via",
        "workflow",
        "workflows",
        "write",
    }

    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None):
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR

    def list_skills(
        self,
        filter_unavailable: bool = True,
        available_tools: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """List all available skills, preferring workspace overrides."""
        skills_by_name: dict[str, dict[str, str]] = {}

        def collect(root: Path, source: str) -> None:
            if not root.exists():
                return
            for skill_dir in sorted(root.iterdir(), key=lambda item: item.name):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue
                skills_by_name.setdefault(
                    skill_dir.name,
                    {
                        "name": skill_dir.name,
                        "path": str(skill_file),
                        "source": source,
                    },
                )

        collect(self.workspace_skills, "workspace")
        if self.builtin_skills:
            collect(self.builtin_skills, "builtin")

        skills = list(skills_by_name.values())
        if filter_unavailable:
            return [
                skill
                for skill in skills
                if self._has_required_tools(
                    self.get_skill_capabilities(skill["name"]),
                    available_tools,
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
        """Load selected skills into a bounded prompt section."""
        parts = []
        seen: set[str] = set()

        for name in skill_names:
            if name in seen:
                continue
            seen.add(name)

            content = self.load_skill(name)
            if not content:
                continue

            content = self._strip_frontmatter(content)
            if len(content) > 3000:
                content = f"{content[:3000].rstrip()}\n\n[... skill content truncated ...]"
            parts.append(f"### Skill: {name}\n\n{content}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def build_skills_summary(
        self,
        available_tools: set[str] | None = None,
    ) -> str:
        """Build an XML summary of all skills."""
        all_skills = self.list_skills(
            filter_unavailable=False,
            available_tools=available_tools,
        )
        if not all_skills:
            return ""

        def escape_xml(text: str) -> str:
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines = ["<skills>"]
        for skill in all_skills:
            name = escape_xml(skill["name"])
            path = skill["path"]
            description = escape_xml(self._get_skill_description(skill["name"]))
            capabilities = self.get_skill_capabilities(skill["name"])

            lines.append('  <skill available="true">')
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{description}</description>")
            lines.append(f"    <location>{path}</location>")
            lines.append(f"    <source>{escape_xml(skill['source'])}</source>")

            if capabilities.get("triggers"):
                trigger_text = escape_xml(", ".join(capabilities["triggers"]))
                lines.append(f"    <triggers>{trigger_text}</triggers>")
            if capabilities.get("tools"):
                tool_text = escape_xml(", ".join(capabilities["tools"]))
                lines.append(f"    <tools>{tool_text}</tools>")
            if capabilities.get("allowed_tools"):
                allowed_tools_text = escape_xml(", ".join(capabilities["allowed_tools"]))
                lines.append(f"    <allowed_tools>{allowed_tools_text}</allowed_tools>")

            lines.append("  </skill>")

        lines.append("</skills>")
        return "\n".join(lines)

    def _get_skill_description(self, name: str) -> str:
        """Get the description of a skill from its frontmatter."""
        metadata = self.get_skill_metadata(name)
        if metadata:
            if metadata.get("description"):
                return str(metadata["description"])
            nested_metadata = metadata.get("metadata")
            if isinstance(nested_metadata, dict) and nested_metadata.get("description"):
                return str(nested_metadata["description"])
        return name

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from markdown content."""
        _, body = self._extract_frontmatter(content)
        return body.strip()

    def _parse_medclaw_metadata(self, raw: str) -> dict[str, Any]:
        """Parse MedClaw-specific metadata from frontmatter."""
        if isinstance(raw, dict):
            return raw.get("medclaw", raw)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return data.get("medclaw", {}) if isinstance(data, dict) else {}

    def get_skill_capabilities(self, name: str) -> dict[str, Any]:
        """Get normalized capability metadata used for routing."""
        frontmatter = self.get_skill_metadata(name) or {}
        medclaw_meta = self._get_skill_meta(name)
        derived_triggers = self._derive_triggers(name, frontmatter)
        allowed_tools = self._normalize_metadata_list(
            frontmatter.get("allowed-tools") or frontmatter.get("allowed_tools")
        )
        tools = self._normalize_metadata_list(medclaw_meta.get("tools", [])) or allowed_tools

        return {
            "triggers": self._normalize_metadata_list(medclaw_meta.get("triggers", []))
            or derived_triggers,
            "output": medclaw_meta.get("output"),
            "risk": medclaw_meta.get("risk"),
            "freshness": medclaw_meta.get("freshness"),
            "tools": tools,
            "required_tools": self._normalize_metadata_list(
                medclaw_meta.get("required_tools", [])
            ),
            "domains": self._normalize_metadata_list(medclaw_meta.get("domains", [])),
            "allowed_tools": allowed_tools,
        }

    def _get_skill_meta(self, name: str) -> dict[str, Any]:
        """Get MedClaw metadata for a skill."""
        metadata = self.get_skill_metadata(name) or {}
        return self._parse_medclaw_metadata(metadata.get("metadata", ""))

    @staticmethod
    def _normalize_metadata_list(value: Any) -> list[str]:
        """Normalize metadata into a stable list of strings."""
        if value is None:
            return []

        if isinstance(value, str):
            parsed = SkillsLoader._parse_frontmatter_value(value)
            if isinstance(parsed, list):
                value = parsed
            elif "," in value:
                value = [item.strip() for item in value.split(",")]
            else:
                value = [value]

        if isinstance(value, tuple | set):
            value = list(value)

        if not isinstance(value, list):
            return []

        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _has_required_tools(
        capabilities: dict[str, Any],
        available_tools: set[str] | None,
    ) -> bool:
        """Return True when runtime tool availability satisfies required tools."""
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
        """Return the most relevant skills for a user request."""
        return [
            skill["name"]
            for skill in self.suggest_skills_for_request(
                text,
                limit=3,
                available_tools=available_tools,
            )
        ]

    def search_local_skills(
        self,
        text: str,
        limit: int = 5,
        available_tools: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """Search local skills by name, description, and derived keywords."""
        return self.suggest_skills_for_request(
            text,
            limit=limit,
            available_tools=available_tools,
        )

    def suggest_skills_for_request(
        self,
        text: str,
        limit: int = 5,
        available_tools: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """Rank skills for a request using names, frontmatter, and descriptions."""
        query = text.lower().strip()
        if not query:
            return []

        query_tokens = self._keyword_tokens(query, min_len=2)
        ranked: list[tuple[float, dict[str, str]]] = []

        for skill in self.list_skills(
            filter_unavailable=True,
            available_tools=available_tools,
        ):
            description = self._get_skill_description(skill["name"])
            capabilities = self.get_skill_capabilities(skill["name"])
            score, reasons = self._score_skill_match(
                query=query,
                query_tokens=query_tokens,
                name=skill["name"],
                description=description,
                triggers=capabilities.get("triggers", []),
            )
            if score <= 0:
                continue

            if skill["source"] == "workspace":
                score += 5

            ranked.append(
                (
                    score,
                    {
                        **skill,
                        "description": description,
                        "relevance_score": f"{score:.1f}",
                        "reasons": ", ".join(reasons[:3]),
                    },
                )
            )

        ranked.sort(key=lambda item: (-item[0], item[1]["name"]))
        return [item for _, item in ranked[:limit]]

    def get_skill_metadata(self, name: str) -> dict[str, Any] | None:
        """Get metadata from a skill's frontmatter."""
        content = self.load_skill(name)
        if not content:
            return None

        frontmatter, _ = self._extract_frontmatter(content)
        return frontmatter

    @staticmethod
    def _extract_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
        """Split markdown frontmatter from the body."""
        if not content.startswith("---"):
            return None, content

        match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
        if not match:
            return None, content

        return SkillsLoader._parse_frontmatter(match.group(1)), content[match.end():]

    @staticmethod
    def _parse_frontmatter(raw: str) -> dict[str, Any]:
        """Parse simple YAML-like frontmatter values."""
        metadata: dict[str, Any] = {}
        current_list_key: str | None = None

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("- ") and current_list_key:
                metadata.setdefault(current_list_key, []).append(
                    SkillsLoader._parse_frontmatter_value(stripped[2:].strip())
                )
                continue

            if ":" not in line:
                current_list_key = None
                continue

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                current_list_key = None
                continue

            if not value:
                metadata[key] = []
                current_list_key = key
                continue

            metadata[key] = SkillsLoader._parse_frontmatter_value(value)
            current_list_key = None

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
                if value.startswith("[") and value.endswith("]"):
                    inner = value[1:-1].strip()
                    if not inner:
                        return []
                    return [
                        item.strip().strip('"').strip("'")
                        for item in inner.split(",")
                        if item.strip()
                    ]
                return value

        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
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

    def _derive_triggers(self, name: str, frontmatter: dict[str, Any]) -> list[str]:
        """Derive fallback triggers from skill name and description."""
        phrases = [
            name.lower(),
            name.lower().replace("-", " "),
            str(frontmatter.get("name", "")).strip().lower(),
        ]
        triggers = [phrase for phrase in phrases if phrase]

        description = str(frontmatter.get("description", ""))
        for token in self._keyword_tokens(description):
            if token not in triggers:
                triggers.append(token)

        return triggers[:12]

    def _score_skill_match(
        self,
        query: str,
        query_tokens: set[str],
        name: str,
        description: str,
        triggers: list[str],
    ) -> tuple[float, list[str]]:
        """Score a skill against a user request."""
        score = 0.0
        reasons: list[str] = []

        normalized_name = name.lower().replace("-", " ")
        name_tokens = self._keyword_tokens(name)
        description_tokens = self._keyword_tokens(description)
        trigger_phrases = [trigger.lower() for trigger in triggers if trigger]

        if normalized_name and normalized_name in query:
            score += 10
            reasons.append("exact name match")

        for trigger in trigger_phrases:
            if len(trigger) >= 3 and trigger in query:
                score += 6
                reasons.append(f"matched trigger '{trigger}'")

        token_hits = query_tokens & name_tokens
        if token_hits:
            score += 3 * len(token_hits)
            reasons.append(f"name tokens: {', '.join(sorted(token_hits)[:3])}")

        description_hits = query_tokens & description_tokens
        if description_hits:
            score += 1.5 * len(description_hits)
            reasons.append(f"description tokens: {', '.join(sorted(description_hits)[:3])}")

        if score < 3:
            return 0.0, []

        return score, reasons

    @classmethod
    def _keyword_tokens(cls, text: str, min_len: int = 3) -> set[str]:
        """Extract useful keyword tokens from free text."""
        return {
            token
            for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", text.lower())
            if len(token) >= min_len and token not in cls._STOPWORDS
        }
