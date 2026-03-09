"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from medclaw.agent.context import ContextBuilder
from medclaw.agent.memory import MemoryStore
from medclaw.agent.processor import MessageProcessor
from medclaw.agent.skills import SkillsLoader
from medclaw.providers.base import LLMProvider

if TYPE_CHECKING:
    from medclaw.config.schema import MedClawConfig


class AgentLoop:
    """The agent loop is the core processing engine.

    It:
    1. Receives messages
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _TOOL_RESULT_MAX_CHARS = 500

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        memory_window: int = 100,
        memory_layer: str = "L1",
    ):
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.memory_layer = memory_layer

        self.context = ContextBuilder(workspace)
        self.context.set_memory_layer(self.memory_layer)
        self.memory_store = MemoryStore(workspace)
        self.skills_loader = SkillsLoader(workspace)
        self.processor = MessageProcessor(provider, workspace, self.skills_loader)
        
        try:
            from medclaw.agent.tools.medical.tools import get_all_tools
            self.available_tools = get_all_tools()
        except Exception:
            self.available_tools = []

    async def run(self, user_message: str, history: list[dict[str, Any]] | None = None) -> str:
        """Run the agent loop for a single message."""
        matched_skills = self.skills_loader.match_skills_for_request(user_message)

        logger.info(f"Matched skills: {matched_skills}")

        # DeepSeek doesn't support function calling, use basic chat
        response = await self.processor.process(
            user_message=user_message,
            history=history,
            skills=matched_skills if matched_skills else None,
        )

        return response

    async def run_with_tools(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        skills: list[str] | None = None,
    ) -> str:
        """Run the agent loop with tool calling support."""
        matched_skills = self.skills_loader.match_skills_for_request(user_message)
        skills_to_use = skills or matched_skills

        logger.info(f"Matched skills: {matched_skills}")

        response, tool_calls = await self.processor.process_with_tools(
            user_message=user_message,
            history=history,
            skills=skills_to_use,
            tools=self.available_tools,
        )

        if tool_calls:
            logger.info(f"Tool calls: {tool_calls}")
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                history = history or []
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": response})
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": result
                })
                response = await self.provider.chat(history)

        return response

    async def _execute_tool(self, tool_call: dict[str, Any]) -> str:
        """Execute a tool call and return the result."""
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        logger.info(f"Executing tool: {tool_name}")

        try:
            from medclaw.agent.tools.medical.tools import execute_tool
            result = await execute_tool(tool_name, arguments)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    def get_skills_summary(self) -> str:
        """Get summary of all available skills."""
        return self.skills_loader.build_skills_summary()

    def search_skills(self, query: str) -> list[dict[str, str]]:
        """Search skills by query."""
        return self.skills_loader.search_local_skills(query)
