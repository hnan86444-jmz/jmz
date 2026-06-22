"""Provider-compatible LLM + MCP JSON tool loop for task agents."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from a2a_mcp.common.utils import get_langchain_openai_kwargs, get_llm_model

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[Any]]

MAX_TOOL_STEPS = 6


@dataclass(frozen=True)
class ToolSpec:
    """Declarative description of a tool the model is allowed to call."""

    name: str
    description: str
    required_args: tuple[str, ...] = ()
    optional_args: tuple[str, ...] = ()


def parse_model_json(text: Any) -> dict[str, Any] | str:
    """Parse a model response that should contain one JSON object."""

    if isinstance(text, list):
        parts: list[str] = []
        for item in text:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        text = "\n".join(parts)

    if not isinstance(text, str):
        return str(text)

    candidate = text.strip()
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
        match = re.search(pattern, candidate, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            break

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else candidate
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if 0 <= start < end:
        snippet = candidate[start : end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else candidate
        except json.JSONDecodeError:
            logger.debug("Could not parse model JSON snippet")

    return candidate


class JSONMCPToolRuntime:
    """Run a JSON-based MCP tool loop without native tool-call history."""

    def __init__(self, instructions: str, tool_specs: list[ToolSpec]):
        self.instructions = instructions.strip()
        self.tool_specs = tool_specs
        self._llm: ChatOpenAI | None = None
        self._threads: dict[str, dict[str, Any]] = {}

    async def ensure_model(self) -> None:
        if self._llm is not None:
            return
        self._llm = ChatOpenAI(
            model_name=get_llm_model(),
            temperature=0.0,
            **get_langchain_openai_kwargs(),
        )

    def clear_thread(self, thread_id: str) -> None:
        self._threads.pop(thread_id, None)

    def _get_thread_state(self, thread_id: str) -> dict[str, Any]:
        return self._threads.setdefault(
            thread_id,
            {
                "history": [],
                "observations": [],
            },
        )

    def _render_tool_specs(self) -> str:
        lines = []
        for spec in self.tool_specs:
            required = ", ".join(spec.required_args) or "(none)"
            optional = ", ".join(spec.optional_args) or "(none)"
            lines.append(
                f"- {spec.name}: {spec.description} | required args: {required} | optional args: {optional}"
            )
        return "\n".join(lines)

    def _render_history(self, history: list[dict[str, str]]) -> str:
        if not history:
            return "(none)"
        return "\n".join(
            f"{item['role'].title()}: {item['content']}" for item in history
        )

    def _render_observations(self, observations: list[dict[str, Any]]) -> str:
        if not observations:
            return "(none)"

        rendered: list[str] = []
        for idx, item in enumerate(observations, start=1):
            payload = {
                "tool": item["tool"],
                "arguments": item["arguments"],
                "result": item["result"],
            }
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            if len(text) > 4000:
                text = text[:4000] + "\n...<truncated>"
            rendered.append(f"{idx}. {text}")
        return "\n".join(rendered)

    def _build_messages(self, thread_id: str) -> list[Any]:
        state = self._get_thread_state(thread_id)
        loop_prompt = f"""
{self.instructions}

You are operating in a provider-compatible JSON tool loop.
Do not use native function calling, tool messages, markdown, or code fences.
Return exactly one JSON object and nothing else.

Allowed response shapes:
1. Request more info:
{{"status":"input_required","question":"..."}}
2. Ask the runtime to call one MCP tool:
{{"status":"tool_call","tool":"tool_name","arguments":{{...}}}}
3. Final answer:
Return the booking/result JSON required by the RESPONSE section in the instructions.
The final object must include a status field such as "completed" or "booking_complete".

Rules:
- Only use tools from the allowed list below.
- Ask at most one focused follow-up question at a time.
- If a tool result is empty or contains an error, either try a narrower/broader search or ask the user a targeted question.
- When you already have enough information and results, produce the final booking JSON directly.

Allowed tools:
{self._render_tool_specs()}
""".strip()

        user_prompt = f"""
Conversation history:
{self._render_history(state["history"])}

Tool observations:
{self._render_observations(state["observations"])}

Decide the single next JSON object now.
""".strip()
        return [
            SystemMessage(content=loop_prompt),
            HumanMessage(content=user_prompt),
        ]

    def _validate_tool_call(self, decision: dict[str, Any]) -> dict[str, Any] | None:
        tool_name = str(decision.get("tool") or "").strip()
        spec = next((item for item in self.tool_specs if item.name == tool_name), None)
        if spec is None:
            return {
                "error": f"Unsupported tool {tool_name!r}.",
                "allowed_tools": [item.name for item in self.tool_specs],
            }

        arguments = decision.get("arguments")
        if not isinstance(arguments, dict):
            return {
                "error": "Tool call arguments must be a JSON object.",
                "tool": tool_name,
            }

        missing = [name for name in spec.required_args if name not in arguments]
        if missing:
            return {
                "error": "Missing required tool arguments.",
                "tool": tool_name,
                "missing": missing,
            }
        return None

    async def run(
        self,
        *,
        query: str,
        thread_id: str,
        execute_tool: ToolExecutor,
    ) -> dict[str, Any] | str:
        await self.ensure_model()
        state = self._get_thread_state(thread_id)
        state["history"].append({"role": "user", "content": query})

        for step in range(1, MAX_TOOL_STEPS + 1):
            assert self._llm is not None
            raw = await self._llm.ainvoke(self._build_messages(thread_id))
            decision = parse_model_json(getattr(raw, "content", raw))
            logger.info("JSON tool loop step %s response: %s", step, decision)

            if not isinstance(decision, dict):
                state["history"].append({"role": "assistant", "content": str(decision)})
                return str(decision)

            status = str(decision.get("status") or "").strip().lower()
            if status == "input_required":
                question = str(decision.get("question") or "").strip()
                if not question:
                    question = "Please provide the missing trip details to continue."
                    decision["question"] = question
                state["history"].append({"role": "assistant", "content": question})
                return decision

            if status == "tool_call":
                tool_name = str(decision.get("tool") or "").strip()
                arguments = decision.get("arguments")
                validation_error = self._validate_tool_call(decision)
                if validation_error is not None:
                    observation = validation_error
                else:
                    assert isinstance(arguments, dict)
                    try:
                        observation = await execute_tool(tool_name, arguments)
                    except Exception as exc:
                        logger.exception("Tool execution failed for %s", tool_name)
                        observation = {
                            "error": str(exc),
                            "tool": tool_name,
                        }

                state["observations"].append(
                    {
                        "tool": tool_name,
                        "arguments": arguments if isinstance(arguments, dict) else {},
                        "result": observation,
                    }
                )
                continue

            state["history"].append(
                {
                    "role": "assistant",
                    "content": json.dumps(decision, ensure_ascii=False),
                }
            )
            return decision

        return {
            "status": "input_required",
            "question": "I need a bit more direction to complete this booking. Please clarify your preference and I will continue.",
        }
