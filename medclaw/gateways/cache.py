"""Small in-process TTL cache for gateway responses."""

from __future__ import annotations

import time
from typing import Any


class SimpleTTLCache:
    """Minimal TTL cache for repeated gateway calls within a process."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return cached value when still fresh."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        created_at, value = entry
        if time.time() - created_at > self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> Any:
        """Store a value and return it."""
        self._entries[key] = (time.time(), value)
        return value
