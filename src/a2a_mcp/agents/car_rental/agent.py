# type: ignore
"""
租车 Agent：基于 LangGraph ReAct + MCP 工具，仅负责租车预订。
独立实现，不与其他任务 Agent 共享代码。
"""
import json
import logging
import re

from collections.abc import AsyncIterable
from typing import Any

from a2a_mcp.common.base_agent import BaseAgent
from a2a_mcp.common.llm_mcp_json_agent import JSONMCPToolRuntime, ToolSpec

from .mcp_client import call_tool, init_default_session, parse_tool_text_json
from . import prompts
from .utils import init_api_key

logger = logging.getLogger(__name__)


class CarRentalAgent(BaseAgent):
    """租车预订 Agent：LangGraph ReAct + MCP 工具，工具首次使用时从 MCP 服务器加载。"""

    def __init__(self):
        init_api_key()
        super().__init__(
            agent_name="CarRentalBookingAgent",
            description="Book rental cars given a criteria",
            content_types=["text", "text/plain"],
        )
        logger.info("Init %s (LLM + MCP JSON loop)", self.agent_name)
        self.instructions = prompts.CARS_COT_INSTRUCTIONS
        self._runtime = JSONMCPToolRuntime(
            instructions=self.instructions,
            tool_specs=[
                ToolSpec(
                    name="search_rental_cars",
                    description="Search rental cars by city, car type, and optional result limit.",
                    required_args=("city",),
                    optional_args=("type_of_car", "limit"),
                ),
                ToolSpec(
                    name="get_travel_inventory",
                    description="Inspect supported rental-car cities and vehicle types.",
                ),
                ToolSpec(
                    name="get_travel_schema",
                    description="Inspect the travel database schema and sample queries.",
                ),
                ToolSpec(
                    name="query_travel_data",
                    description="Run a fallback SELECT query against the travel database.",
                    required_args=("query",),
                ),
            ],
        )

    async def _ensure_agent(self) -> None:
        await self._runtime.ensure_model()

    async def invoke(self, query: str, session_id: str) -> dict[str, Any]:
        raise NotImplementedError("Please use the streaming function")

    async def stream(
        self, query: str, context_id: str, task_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        logger.info("Running %s stream for session %s %s", self.agent_name, context_id, task_id)
        if not query:
            raise ValueError("Query cannot be empty")
        await self._ensure_agent()
        thread_id = context_id or task_id
        yield {
            "response_type": "text",
            "is_task_complete": False,
            "require_user_input": False,
            "content": f"{self.agent_name}: Processing Request...",
        }
        async with init_default_session() as session:
            response_content = await self._runtime.run(
                query=query,
                thread_id=thread_id,
                execute_tool=lambda name, arguments: _call_and_parse(
                    session, name, arguments
                ),
            )
        if _is_final_response(response_content):
            self._runtime.clear_thread(thread_id)
        yield self.get_agent_response(response_content)

    def format_response(self, chunk: str | dict) -> Any:
        if isinstance(chunk, dict):
            return chunk
        for pattern in [r"```\n(.*?)\n```", r"```json\s*(.*?)\s*```", r"```tool_outputs\s*(.*?)\s*```"]:
            match = re.search(pattern, chunk, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    return match.group(1).strip()
        return chunk

    def get_agent_response(self, chunk: str | dict) -> dict[str, Any]:
        data = self.format_response(chunk)
        try:
            if isinstance(data, dict):
                if str(data.get("status") or "").strip().lower() == "input_required":
                    return {"response_type": "text", "is_task_complete": False, "require_user_input": True, "content": data.get("question", "")}
                return {"response_type": "data", "is_task_complete": True, "require_user_input": False, "content": data}

            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict):
                        if str(parsed.get("status") or "").strip().lower() == "input_required":
                            return {"response_type": "text", "is_task_complete": False, "require_user_input": True, "content": parsed.get("question", "")}
                        return {"response_type": "data", "is_task_complete": True, "require_user_input": False, "content": parsed}
                except (TypeError, json.JSONDecodeError):
                    pass
                return {"response_type": "text", "is_task_complete": True, "require_user_input": False, "content": data}

            return {"response_type": "text", "is_task_complete": True, "require_user_input": False, "content": str(data)}
        except Exception as e:
            logger.error("Error in get_agent_response: %s", e)
            return {"response_type": "text", "is_task_complete": True, "require_user_input": False, "content": "Could not complete booking. Please try again."}


async def _call_and_parse(session, name: str, arguments: dict[str, Any]) -> Any:
    result = await call_tool(session, name, arguments)
    return parse_tool_text_json(result)


def _is_final_response(chunk: str | dict) -> bool:
    if not isinstance(chunk, dict):
        return True
    return str(chunk.get("status") or "").strip().lower() != "input_required"
