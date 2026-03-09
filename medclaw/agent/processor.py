"""Message processor for agent conversations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger

from medclaw.agent.context import ContextBuilder
from medclaw.agent.memory import MemoryStore
from medclaw.agent.skills import SkillsLoader
from medclaw.providers.base import LLMProvider


class MessageProcessor:
    """Process messages through the agent."""

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        skills_loader: SkillsLoader | None = None,
    ):
        self.provider = provider
        self.workspace = workspace
        self.context = ContextBuilder(workspace)
        self.skills_loader = skills_loader or SkillsLoader(workspace)
        self.memory_store = MemoryStore(workspace)

    async def process(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
    ) -> str:
        """Process a user message and return the response."""
        context = self.context.build_context(user_message, history, skills)

        messages = []
        messages.append({"role": "system", "content": context["system"]})

        for msg in context.get("history", []):
            messages.append(msg)

        messages.append({"role": "user", "content": context["user_message"]})

        if "memories" in context:
            memory_section = "\n## Relevant Memories\n"
            for mem in context["memories"]:
                memory_section += f"- {mem.get('content', '')[:200]}\n"
            messages[0]["content"] += memory_section

        try:
            response = await self.provider.chat(messages)
            self.memory_store.save(
                user_message,
                {"response": response, "skills": skills or []}
            )
            return response
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    async def process_with_tools(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Process message with tool calling support."""
        context = self.context.build_context(user_message, history, skills)

        messages = []
        messages.append({"role": "system", "content": context["system"]})

        for msg in context.get("history", []):
            messages.append(msg)

        messages.append({"role": "user", "content": context["user_message"]})

        response, tool_calls = await self.provider.chat_with_tools(
            messages, tools=tools or []
        )

        return response, tool_calls
