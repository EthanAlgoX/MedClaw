"""Memory store for agent conversations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryStore:
    """Store and retrieve conversation memories."""

    def __init__(self, workspace: Path, layer: str = "L1"):
        self.workspace = workspace
        self.memory_path = workspace / "memory"
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.layer = layer

    def save(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Save a memory entry."""
        entry = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        (self.memory_path / filename).write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8"
        )

    def retrieve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant memories."""
        memories = []

        for file in sorted(self.memory_path.glob("*.json"), reverse=True)[:50]:
            try:
                entry = json.loads(file.read_text(encoding="utf-8"))
                entry["file"] = str(file.name)
                memories.append(entry)
            except Exception:
                continue

        return memories[:limit]

    def search(self, keyword: str) -> list[dict[str, Any]]:
        """Search memories by keyword."""
        results = []

        for file in self.memory_path.glob("*.json"):
            try:
                content = file.read_text(encoding="utf-8")
                if keyword.lower() in content.lower():
                    results.append(json.loads(content))
            except Exception:
                continue

        return results
