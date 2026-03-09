"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> str:
        """Send a chat request and return the response."""
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send a chat request with tool calling support."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model name."""
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        pass
