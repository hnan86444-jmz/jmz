"""
编排器专用：基于 LangGraph 的编排工作流，不与其他 agent 共享。

图结构：START -> [planner | execute_one] -> ... -> END。
"""
import json
import logging
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Any, TypedDict
from uuid import uuid4

import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)
from langgraph.graph import END, START, StateGraph

from a2a_mcp.agents.orchestrator.mcp_client import (
    find_agent as mcp_find_agent,
    find_resource as mcp_find_resource,
    init_session as mcp_init_session,
)
from a2a_mcp.agents.orchestrator.utils import get_mcp_server_config

logger = logging.getLogger(__name__)


class OrchestrationState(TypedDict, total=False):
    task_id: str
    context_id: str
    user_query: str
    query_history: list[str]
    planned_tasks: list[dict[str, Any]]
    task_index: int
    results: list[Any]
    travel_context: dict[str, Any]
    paused: bool
    pause_question: str | None
    paused_step: str | None
    resume_current_task: bool
    done: bool
    buffered_chunks: list[Any]


@dataclass(frozen=True)
class A2AStreamResult:
    chunks: list[Any]
    artifact: Any | None = None
    paused: bool = False
    pause_question: str | None = None


async def _run_a2a_call(
    *,
    agent_card: AgentCard,
    query: str,
    task_id: str,
    context_id: str,
) -> A2AStreamResult:
    chunks: list[Any] = []
    artifact = None
    paused = False
    pause_question: str | None = None

    # 流式调用 planner/子 agent 时 LLM 可能较慢；超时过短易 ReadTimeout，过长会“一直无法返回”
    # 可通过环境变量 A2A_STREAM_TIMEOUT（秒）调整，默认 120
    timeout_sec = float(os.getenv("A2A_STREAM_TIMEOUT", "120"))
    timeout = httpx.Timeout(timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        a2a = A2AClient(httpx_client, agent_card)
        payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "messageId": uuid4().hex,
                "contextId": context_id,
            },
        }
        request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**payload)
        )
        async for chunk in a2a.send_message_streaming(request):
            chunks.append(chunk)
            if isinstance(chunk.root, SendStreamingMessageSuccessResponse):
                event = chunk.root.result
                if isinstance(event, TaskArtifactUpdateEvent):
                    artifact = event.artifact
                if isinstance(event, TaskStatusUpdateEvent):
                    if event.status.state == TaskState.input_required:
                        paused = True
                        try:
                            pause_question = (
                                event.status.message.parts[0].root.text  # type: ignore[attr-defined]
                            )
                        except Exception:
                            pause_question = None
                        break
                    # 某些服务端可能不会及时关闭 SSE 连接；收到终态后可直接停止读取，避免“卡住”
                    if event.status.state in (
                        TaskState.completed,
                        TaskState.failed,
                        TaskState.canceled,
                        TaskState.rejected,
                        TaskState.auth_required,
                    ):
                        break

    return A2AStreamResult(
        chunks=chunks, artifact=artifact, paused=paused, pause_question=pause_question
    )


async def _get_planner_card() -> AgentCard:
    config = get_mcp_server_config()
    async with mcp_init_session(
        config.host, config.port, config.transport
    ) as session:
        response = await mcp_find_resource(
            session, "resource://agent_cards/planner_agent"
        )
        if not response.contents:
            raise ValueError("Planner agent card resource has no contents")
        data = json.loads(response.contents[0].text)
        cards = data.get("agent_card") or []
        if not cards:
            raise ValueError("Planner agent card list is empty")
        return AgentCard(**cards[0])


async def _find_task_agent_card(task_description: str) -> AgentCard:
    config = get_mcp_server_config()
    async with mcp_init_session(
        config.host, config.port, config.transport
    ) as session:
        result = await mcp_find_agent(session, task_description)
        if not getattr(result, "content", None) or not result.content:
            raise ValueError("find_agent returned no content")
        agent_card_json = json.loads(result.content[0].text)
        return AgentCard(**agent_card_json)


async def node_planner(state: OrchestrationState) -> OrchestrationState:
    planner_card = await _get_planner_card()
    result = await _run_a2a_call(
        agent_card=planner_card,
        query=state.get("user_query") or "",
        task_id=state.get("task_id") or "",
        context_id=state.get("context_id") or "",
    )

    new_state: OrchestrationState = {
        "buffered_chunks": result.chunks,
        "paused": result.paused,
        "pause_question": result.pause_question,
        "paused_step": "planner" if result.paused else None,
    }

    if result.artifact is not None:
        results = list(state.get("results", []))
        results.append(result.artifact)
        new_state["results"] = results

        if getattr(result.artifact, "name", None) == "PlannerAgent-result":
            try:
                artifact_data = result.artifact.parts[0].root.data  # type: ignore[attr-defined]
                tasks = artifact_data.get("tasks", [])
                new_state["planned_tasks"] = tasks
                new_state["task_index"] = 0
                if "trip_info" in artifact_data:
                    new_state["travel_context"] = artifact_data["trip_info"]
            except Exception:
                logger.exception("解析 Planner artifact 失败")

    return new_state


async def node_execute_one(state: OrchestrationState) -> OrchestrationState:
    planned = state.get("planned_tasks", [])
    idx = int(state.get("task_index", 0))
    if idx >= len(planned):
        return {"done": True, "buffered_chunks": []}

    task = planned[idx]
    description = task.get("description") or json.dumps(task, ensure_ascii=False)

    agent_card = await _find_task_agent_card(description)
    query_to_send = (
        state["user_query"] if state.get("resume_current_task") else description
    )
    result = await _run_a2a_call(
        agent_card=agent_card,
        query=query_to_send,
        task_id=state.get("task_id") or "",
        context_id=state.get("context_id") or "",
    )

    new_state: OrchestrationState = {
        "buffered_chunks": result.chunks,
        "paused": result.paused,
        "pause_question": result.pause_question,
        "paused_step": "execute_one" if result.paused else None,
    }

    if result.artifact is not None:
        results = list(state.get("results", []))
        results.append(result.artifact)
        new_state["results"] = results

    if not result.paused:
        new_state["resume_current_task"] = False
        new_state["task_index"] = idx + 1
        if new_state["task_index"] >= len(planned):
            new_state["done"] = True

    return new_state


def route_after_planner(state: OrchestrationState) -> str:
    if state.get("paused"):
        return END
    if not state.get("planned_tasks"):
        return END
    return "execute_one"


def route_after_execute(state: OrchestrationState) -> str:
    if state.get("paused"):
        return END
    if state.get("done"):
        return END
    return "execute_one"


def build_orchestration_graph():
    g: StateGraph = StateGraph(OrchestrationState)  # type: ignore[arg-type]
    g.add_node("planner", node_planner)
    g.add_node("execute_one", node_execute_one)

    def route_start(state: OrchestrationState) -> str:
        if state.get("done"):
            return END
        planned = state.get("planned_tasks") or []
        idx = int(state.get("task_index", 0))
        if planned and idx < len(planned):
            return "execute_one"
        return "planner"

    g.add_conditional_edges(START, route_start)
    g.add_conditional_edges("planner", route_after_planner)
    g.add_conditional_edges("execute_one", route_after_execute)
    return g.compile()


async def run_orchestration_stream(
    *,
    graph,
    initial_state: OrchestrationState,
) -> AsyncIterable[OrchestrationState]:
    async for values in graph.astream(initial_state, stream_mode="values"):
        yield values
