"""
A2A GenericAgentExecutor：连接 A2A 服务端（RequestContext、EventQueue）与我们的 Agent。

调用 agent.stream(query, context_id, task_id)；将 A2A 事件（TaskStatusUpdateEvent、
TaskArtifactUpdateEvent）转发到队列；将 dict 响应映射为 updater.add_artifact / update_status / complete。
"""
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    InvalidParamsError,
    SendStreamingMessageSuccessResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from a2a_mcp.common.base_agent import BaseAgent


logger = logging.getLogger(__name__)


class GenericAgentExecutor(AgentExecutor):
    """旅行类 Agent 的 A2A 执行器：运行 agent.stream() 并将事件/artifact 推送到队列。"""

    def __init__(self, agent: BaseAgent):
        self.agent = agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        logger.info(f'Executing agent {self.agent.agent_name}')
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()

        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        finished = False
        last_text: str = ""
        try:
            async for item in self.agent.stream(query, task.context_id, task.id):
                # item 为 A2A chunk（带 .root 且为 SendStreamingMessageSuccessResponse）或本项目的 agent 返回的 dict
                if hasattr(item, "root") and isinstance(
                    item.root, SendStreamingMessageSuccessResponse
                ):
                    event = item.root.result
                    if isinstance(
                        event,
                        (TaskStatusUpdateEvent | TaskArtifactUpdateEvent),
                    ):
                        await event_queue.enqueue_event(event)
                    continue

                if not isinstance(item, dict):
                    logger.warning("Agent yielded non-dict item: %s", type(item))
                    continue

                content = item.get("content", "")
                last_text = content if isinstance(content, str) else str(content)

                is_task_complete = item.get("is_task_complete", False)
                require_user_input = item.get("require_user_input", False)

                if is_task_complete:
                    if item.get("response_type") == "data":
                        part = DataPart(data=content)
                    else:
                        part = TextPart(text=last_text)

                    await updater.add_artifact(
                        [part],
                        name=f"{self.agent.agent_name}-result",
                    )
                    await updater.complete()
                    finished = True
                    break

                if require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            last_text,
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                    finished = True
                    break

                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        last_text,
                        task.context_id,
                        task.id,
                    ),
                )
        except Exception as e:
            logger.exception("Agent stream raised exception: %s", e)
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(
                    f"Agent 执行异常：{e!r}",
                    task.context_id,
                    task.id,
                ),
                final=True,
            )
            finished = True

        # 兜底：如果 agent.stream 正常结束但没有发出 completed / input_required 终态
        if not finished:
            logger.error(
                "Agent stream ended without final state (agent=%s, task=%s)",
                self.agent.agent_name,
                task.id,
            )
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(
                    (last_text or "Agent 未返回最终结果（completed/input-required）。请检查该 Agent 的 stream 实现。"),
                    task.context_id,
                    task.id,
                ),
                final=True,
            )

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
