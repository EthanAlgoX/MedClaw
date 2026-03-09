"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import Any

import httpx

from medclaw.providers.base import LLMProvider


class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM provider."""

    DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

    MODELS = [
        "anthropic/claude-opus-4-1",
        "anthropic/claude-sonnet-4-20250514",
        "anthropic/claude-3-5-sonnet-20241022",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash-exp",
    ]

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> str:
        """Send a chat request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": kwargs.get("model", self.DEFAULT_MODEL),
            "messages": messages,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send a chat request with tool calling support."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": kwargs.get("model", self.DEFAULT_MODEL),
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        message = data["choices"][0]["message"]
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])

        return content, tool_calls

    def get_default_model(self) -> str:
        """Get the default model name."""
        return self.DEFAULT_MODEL

    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        return self.MODELS.copy()
