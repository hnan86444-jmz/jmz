# type: ignore
"""
Planner Agent：使用自定义 LangGraph StateGraph 实现。

单节点 'plan'：用 PLANNER_COT_INSTRUCTIONS 与用户查询调用 LLM，
结构化输出 ResponseFormat（status、question、content=TaskList）。流式先 yield 中间消息，
再 yield 最终 get_agent_response（input_required / completed / error）。
"""
import ast
import json
import logging
import re

from collections.abc import AsyncIterable
from typing import Any, TypedDict

from a2a_mcp.common.base_agent import BaseAgent
from a2a_mcp.common.utils import get_langchain_openai_kwargs, get_llm_model
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import prompts
from .types import ResponseFormat, TaskList
from .utils import init_api_key

logger = logging.getLogger(__name__)

memory = MemorySaver()


class PlannerState(TypedDict, total=False):
    """Planner 图的状态。"""

    messages: list
    structured_response: Any  # ResponseFormat


def _build_planner_graph():
    """构建 LangGraph：START -> plan（LLM 结构化输出）-> END；使用 MemorySaver 作为检查点。"""
    # init_api_key()
    model = ChatOpenAI(
        model_name=get_llm_model(),
        temperature=0.0,
        **get_langchain_openai_kwargs(),
        # 尽量让 OpenAI 兼容端点强制返回 JSON
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    try:
        structured_llm = model.with_structured_output(ResponseFormat)
    except Exception as e:
        # 某些 OpenAI 兼容模型不支持 with_structured_output；降级为 JSON 文本解析
        structured_llm = None
        logger.warning("Planner structured output not supported, fallback to JSON parsing: %s", e)

    def plan_node(state: PlannerState) -> PlannerState:
        """取最后一条用户消息，调用结构化 LLM，返回 structured_response。"""
        messages = state.get("messages", [])
        last_user = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)),
            None,
        )
        user_query = getattr(last_user, "content", "") if last_user else ""
        prompt_msgs = [
            SystemMessage(content=prompts.PLANNER_COT_INSTRUCTIONS),
            HumanMessage(content=user_query),
        ]
        if structured_llm is not None:
            result = structured_llm.invoke(prompt_msgs)
        else:
            raw = model.invoke(prompt_msgs)
            text = getattr(raw, "content", "")
            if not isinstance(text, str):
                text = str(text)
            candidate = text.strip()
            # 1) 尝试从 code fence 中提取 JSON
            for pat in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
                m = re.search(pat, candidate, re.DOTALL | re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    break
            # 2) 尝试截取第一个 JSON 对象（即使前后有额外文本）
            if "{" in candidate and "}" in candidate:
                start = candidate.find("{")
                end = candidate.rfind("}")
                if 0 <= start < end:
                    candidate = candidate[start : end + 1].strip()

            try:
                # 优先按严格 JSON 解析
                parsed = json.loads(candidate)
            except Exception:
                # 兼容：某些模型会输出 Python dict（单引号）而非 JSON
                try:
                    parsed = ast.literal_eval(candidate)
                except Exception:
                    result = ResponseFormat(
                        status="error",
                        question="Planner 输出无法解析为 JSON。请重试或提供更明确的行程信息。",
                        content=None,
                    )
                    return {"structured_response": result}

            # 允许两种形态：ResponseFormat 或直接 TaskList
            try:
                if isinstance(parsed, dict) and "status" in parsed:
                    result = ResponseFormat.model_validate(parsed)
                elif isinstance(parsed, dict) and "tasks" in parsed:
                    task_list = TaskList.model_validate(parsed)
                    result = ResponseFormat(status="completed", question="", content=task_list)
                elif isinstance(parsed, dict) and "question" in parsed:
                    # 只给了 question 的情况
                    result = ResponseFormat(status="input_required", question=str(parsed.get("question") or ""), content=None)
                else:
                    result = ResponseFormat(
                        status="error",
                        question="Planner 输出结构不符合预期。请重试或提供更明确的行程信息。",
                        content=None,
                    )
            except Exception:
                result = ResponseFormat(
                    status="error",
                    question="Planner 输出无法解析为有效结构。请重试或提供更明确的行程信息。",
                    content=None,
                )
        return {"structured_response": result}

    graph = StateGraph(PlannerState)  # type: ignore[arg-type]
    graph.add_node("plan", plan_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", END)
    return graph.compile(checkpointer=memory)


class LangGraphPlannerAgent(BaseAgent):
    """基于自定义 LangGraph StateGraph 的 Planner Agent。"""

    def __init__(self):
        init_api_key()
        logger.info("Initializing LangGraphPlannerAgent (custom StateGraph)")
        super().__init__(
            agent_name="PlannerAgent",
            description="Breakdown the user request into executable tasks",
            content_types=["text", "text/plain"],
        )
        self._graph = _build_planner_graph()

    def invoke(self, query: str, sessionId: str) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self._graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        )
        return self.get_agent_response(config)

    async def stream(
        self, query: str, sessionId: str, task_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        config = {"configurable": {"thread_id": sessionId}}
        inputs = {"messages": [HumanMessage(content=query)]}

        logger.info(
            "Running LangGraphPlannerAgent stream for session %s %s with input %s",
            sessionId,
            task_id,
            query[:80],
        )

        async for values in self._graph.astream(
            inputs, config=config, stream_mode="values"
        ):
            # 可选：yield 中间状态（如「正在规划…」）
            if values.get("structured_response") is None:
                yield {
                    "response_type": "text",
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Planning your trip...",
                }
        yield self.get_agent_response(config)

    def get_agent_response(self, config: dict) -> dict[str, Any]:
        """将 structured_response（ResponseFormat）映射为 A2A 兼容的 dict（response_type、is_task_complete、content）。
        config 需包含 configurable.thread_id，以便 get_state 取到对应运行状态。"""
        current_state = self._graph.get_state(config)
        structured_response = current_state.values.get("structured_response")
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status == "input_required":
                return {
                    "response_type": "text",
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.question,
                }
            if structured_response.status == "error":
                return {
                    "response_type": "text",
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.question,
                }
            if structured_response.status == "completed":
                return {
                    "response_type": "data",
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.content.model_dump(),
                }
        return {
            "response_type": "text",
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }
