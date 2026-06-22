"""
编排器 Agent：通过 LangGraph + MCP + A2A 协调 Planner 与各 Task Agent。

- 维护会话状态 _state，运行编排图（planner -> 执行任务）。
- 子 agent 返回 input_required 时：尝试 answer_user_question()；若 can_answer 为 yes 则无需用户输入即可继续。
- 全部完成后：生成摘要并 yield 最终响应。
"""
import json
import logging
import os

from collections.abc import AsyncIterable
from typing import Any
from a2a_mcp.common.base_agent import BaseAgent
from a2a_mcp.common.utils import get_llm_model

from . import prompts
from .orchestration import build_orchestration_graph, run_orchestration_stream
from .utils import init_api_key


logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    顶层 Agent：接收用户查询，经 LangGraph 先跑 Planner 再跑各任务 Agent，
    返回摘要或向用户请求输入。编排图定义在本包 orchestration 模块。
    """

    def __init__(self):
        init_api_key()
        super().__init__(
            agent_name="Orchestrator Agent",
            description="Facilitate inter-agent communication",
            content_types=["text", "text/plain"],
        )
        self._orchestration_graph = build_orchestration_graph()
        self._state = None
        self.results: list[Any] = []
        self.travel_context: dict[str, Any] = {}
        self.query_history: list[str] = []
        self.context_id: str | None = None

    async def generate_summary(self) -> str:
        """根据 self.results 使用 SUMMARY_COT_INSTRUCTIONS 提示生成旅行摘要。"""
        client = init_api_key()
        response = client.chat.completions.create(
            model=get_llm_model(),
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": prompts.SUMMARY_COT_INSTRUCTIONS.replace(
                        "{travel_data}", str(self.results)
                    ),
                },
            ],
            temperature=0.0,
        )
        msg = response.choices[0].message
        content = getattr(msg, "content", None)
        return (content if isinstance(content, str) else str(msg)) or ""

    def answer_user_question(self, question: str) -> str:
        """根据 travel_context 与 query_history 尝试回答；返回含 can_answer 与 answer 的 JSON。"""
        try:
            client = init_api_key()
            response = client.chat.completions.create(
                model=get_llm_model(),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": prompts.QA_COT_PROMPT.replace(
                            "{TRIP_CONTEXT}", str(self.travel_context)
                        )
                        .replace("{CONVERSATION_HISTORY}", str(self.query_history))
                        .replace("{TRIP_QUESTION}", question),
                    },
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            msg = response.choices[0].message
            content = getattr(msg, "content", None)
            return (content if isinstance(content, str) else str(msg)) or ""
        except Exception as e:
            logger.info(f"Error answering user question: {e}")
        return '{"can_answer": "no", "answer": "Cannot answer based on provided context"}'

    def clear_state(self) -> None:
        """重置 results、travel_context、query_history 及编排状态，用于新会话。"""
        self.results.clear()
        self.travel_context.clear()
        self.query_history.clear()
        self._state = None

    async def stream(
        self, query: str, context_id: str, task_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        主入口：运行编排图，yield A2A chunk 或 dict 响应。
        暂停时：尝试自动回答；能回答则继续跑图，否则 yield require_user_input。
        完成后：生成摘要并 yield 最终内容。
        """
        logger.info(
            f"Running {self.agent_name} stream for session {context_id}, task {task_id} - {query}"
        )
        if not query:
            raise ValueError("Query cannot be empty")
        if self.context_id != context_id:
            # 会话上下文变化时清空状态
            self.clear_state()
            self.context_id = context_id

        self.query_history.append(query)
        # 初始化或恢复 LangGraph 编排状态
        if not self._state:
            self._state = {
                "task_id": task_id,
                "context_id": context_id,
                "user_query": query,
                "query_history": list(self.query_history),
                "planned_tasks": [],
                "task_index": 0,
                "results": [],
                "travel_context": {},
                "paused": False,
                "pause_question": None,
                "paused_step": None,
                "resume_current_task": False,
                "done": False,
                "buffered_chunks": [],
            }
        else:
            # 本轮更新：若上次在任务中途暂停，则当前 query 视为用户回答
            self._state["user_query"] = query
            self._state["query_history"] = list(self.query_history)
            if self._state.get("paused"):
                self._state["paused"] = False
                self._state["pause_question"] = None
                self._state["auto_answer_attempts"] = 0
                self._state["resume_current_task"] = (
                    self._state.get("paused_step") == "execute_one"
                )
                self._state["paused_step"] = None
            else:
                self._state["resume_current_task"] = False
                self._state["auto_answer_attempts"] = 0

        while True:
            # 跑图直到到达 END（暂停或完成）
            async for values in run_orchestration_stream(
                graph=self._orchestration_graph, initial_state=self._state
            ):
                self._state = values

                # 维护本地镜像供 answer_user_question 与 generate_summary 使用
                if values.get("results") is not None:
                    self.results = list(values.get("results", []))
                if values.get("travel_context") is not None:
                    self.travel_context = dict(values.get("travel_context", {}))

                for chunk in values.get("buffered_chunks", []) or []:
                    yield chunk

            # 图跑完后：若子 agent 请求输入，则尝试根据上下文自动回答
            if self._state and self._state.get("paused"):
                question = self._state.get("pause_question") or ""
                paused_step = self._state.get("paused_step")

                # Planner 的澄清问题通常必须由用户提供（否则会陷入自动回答死循环）
                if paused_step == "planner":
                    yield {
                        "response_type": "text",
                        "is_task_complete": False,
                        "require_user_input": True,
                        "content": question or "请补充更多行程信息以继续。",
                    }
                    return

                max_auto = int(os.getenv("A2A_MAX_AUTO_ANSWER", "2"))
                attempts = int(self._state.get("auto_answer_attempts", 0))
                if attempts >= max_auto:
                    yield {
                        "response_type": "text",
                        "is_task_complete": False,
                        "require_user_input": True,
                        "content": question or "请补充更多信息以继续。",
                    }
                    return

                try:
                    answer_data = json.loads(self.answer_user_question(question))
                    if answer_data.get("can_answer") == "yes":
                        # 编排器可代用户回答，无需用户输入即可继续
                        self._state["auto_answer_attempts"] = attempts + 1
                        self._state["user_query"] = answer_data.get("answer", question)
                        self._state["paused"] = False
                        self._state["pause_question"] = None
                        self._state["resume_current_task"] = (
                            self._state.get("paused_step") == "execute_one"
                        )
                        self._state["paused_step"] = None
                        logger.info("Auto-answered and resuming workflow")
                        continue
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Could not parse answer_user_question result")
                # 无法自动回答，向用户请求输入
                self._state["auto_answer_attempts"] = 0
                yield {
                    "response_type": "text",
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": question or "Please provide more details to continue.",
                }
                return

            if self._state and self._state.get("done"):
                break
            # Planner 未返回任务：标记完成并退出，仍可生成摘要
            if self._state is not None and not self._state.get("planned_tasks"):
                self._state["done"] = True
            break

        if self._state and self._state.get("done"):
            logger.info(f"Generating summary for {len(self.results)} results")
            summary = await self.generate_summary()
            self.clear_state()
            yield {
                "response_type": "text",
                "is_task_complete": True,
                "require_user_input": False,
                "content": summary,
            }
