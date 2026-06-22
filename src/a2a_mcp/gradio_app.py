# type: ignore
"""
Gradio 前端：与编排器 Agent 对话，支持多轮（规划、订票、摘要等）。

使用方式：
  uv run python -m a2a_mcp.gradio_app
  或
  uv run gradio run src/a2a_mcp/gradio_app.py

前置：需先启动 MCP 服务（uv run a2a-mcp）及各任务 Agent（planner、air、hotel、car），
编排器在本进程内运行，会通过 MCP 发现并调用上述 Agent。
"""
import asyncio
import concurrent.futures
import logging
import os
from uuid import uuid4

import gradio as gr

from a2a_mcp.agents import OrchestratorAgent

logger = logging.getLogger(__name__)

# 端口：环境变量 GRADIO_SERVER_PORT 或从 7860 起尝试到 7870
DEFAULT_PORT_RANGE = (7860, 7871)

def _append_messages_history(history: list, user_text: str, assistant_text: str) -> list:
    """追加一轮对话到 gr.Chatbot messages 结构。"""
    h = list(history or [])
    h.append({"role": "user", "content": user_text})
    h.append({"role": "assistant", "content": assistant_text})
    return h


def _get_agent_and_ids():
    """创建编排器实例及会话 ID，供首次对话使用。"""
    agent = OrchestratorAgent()
    return agent, str(uuid4()), str(uuid4())


async def chat(message: str, history: list, state: dict | None) -> tuple[list, dict]:
    """与编排器对话：将用户消息送入 agent.stream，收集最终 content 并追加到对话。"""
    if not message or not message.strip():
        return history or [], state or {}

    if state is None:
        state = {}
    if state.get("agent") is None:
        try:
            agent, cid, tid = _get_agent_and_ids()
            state["agent"] = agent
            state["context_id"] = cid
            state["task_id"] = tid
        except Exception as e:
            logger.exception("初始化编排器失败: %s", e)
            reply = f"初始化失败，请检查环境（如 OPENAI_API_KEY）及 MCP/各 Agent 是否已启动：{e!r}"
            return _append_messages_history(history, message, reply), state

    agent = state["agent"]
    context_id = state["context_id"]
    task_id = state["task_id"]

    reply = ""
    try:
        async for item in agent.stream(message.strip(), context_id, task_id):
            if isinstance(item, dict) and "content" in item:
                content = item["content"]
                reply = content if isinstance(content, str) else str(content)
                if item.get("require_user_input"):
                    reply = f"（需要补充信息）\n\n{reply}"
    except Exception as e:
        logger.exception("编排器 stream 异常: %s", e)
        err_str = str(e).lower()
        if "readtimeout" in err_str or "timeout" in err_str or "503" in err_str:
            reply = "Planner 或子 Agent 响应超时或连接中断，请稍后重试或检查对应服务（如 10102）是否正常。"
        else:
            reply = f"请求出错：{e!r}"

    if not reply:
        reply = "（未收到回复，请确认 MCP 与各 Agent 已启动）"

    new_history = _append_messages_history(history, message, reply)
    return new_history, state


def _run_chat(message: str, history: list, state: dict) -> tuple[list, dict]:
    """在事件循环中运行 chat，返回 (history, state)。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(chat(message, history, state))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(asyncio.run, chat(message, history, state))
        return fut.result()


def chat_sync(message: str, history: list, state: dict | None):
    """同步包装：先立即显示用户消息并清空输入，再获取回复并更新对话。"""
    state = state or {}
    history = history or []
    if not message or not message.strip():
        yield history, state, ""
        return

    # 空消息时的 agent 初始化会失败，需在 chat 里处理，这里先预显
    # 第一次 yield：立即把用户消息加入对话框并清空输入框
    temp_history = _append_messages_history(history, message.strip(), "思考中...")
    yield temp_history, state, ""

    try:
        new_history, new_state = _run_chat(message.strip(), history, state)
        yield new_history, new_state, ""
    except Exception as e:
        logger.exception("chat_sync 异常: %s", e)
        err_str = str(e).lower()
        if "readtimeout" in err_str or "timeout" in err_str or "503" in err_str:
            err_msg = "Planner 或子 Agent 响应超时或连接中断，请稍后重试或检查对应服务是否正常。"
        else:
            err_msg = f"请求出错：{e!r}"
        if "Planner agent card" in str(e) or "no agent cards" in err_str:
            err_msg = "MCP 未加载到 Agent 卡片，请确认已启动 MCP 服务并在项目根目录下存在 agent_cards/*.json。"
        new_history = _append_messages_history(history, message.strip(), err_msg)
        yield new_history, state, ""


def build_ui() -> gr.Blocks:
    """构建 Gradio 界面。"""
    with gr.Blocks(
        title="A2A 旅行助手",
    ) as demo:
        gr.Markdown(
            """
            ## 旅行规划与预订助手
            输入需求（如「帮我规划去北京的行程并订机票酒店」），编排器将协调规划与订票 Agent 并返回摘要。
            **请先启动 MCP 与各 Agent 服务**（见终端说明）。
            """
        )
        state = gr.State(None)
        try:
            chatbot = gr.Chatbot(
                label="对话",
                height=400,
                type="messages",
            )
        except TypeError:
            # 兼容较老版本 gradio（旧版可能没有 type 参数）
            chatbot = gr.Chatbot(
                label="对话",
                height=400,
            )
        msg = gr.Textbox(
            label="输入",
            placeholder="例如：Plan my trip to Beijing",
            lines=2,
            scale=7,
        )
        submit = gr.Button("发送", variant="primary", scale=1)

        submit.click(
            chat_sync,
            inputs=[msg, chatbot, state],
            outputs=[chatbot, state, msg],
        )
        msg.submit(
            chat_sync,
            inputs=[msg, chatbot, state],
            outputs=[chatbot, state, msg],
        )

        gr.Markdown(
            "**说明**：请通过环境变量 `MCP_HOST` / `MCP_PORT` / `MCP_TRANSPORT` 配置 MCP；Planner / 机票 / 酒店 / 租车 Agent 需在对应端口运行。"
        )
    return demo


def main():
    """启动 Gradio 应用；7860 被占用时自动尝试 7861–7870。"""
    demo = build_ui()
    port_str = os.environ.get("GRADIO_SERVER_PORT", "").strip()
    if port_str.isdigit():
        port = int(port_str)
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            show_error=True,
            theme=gr.themes.Soft(),
            css=".message { min-height: 120px; }",
        )
        return
    for port in range(DEFAULT_PORT_RANGE[0], DEFAULT_PORT_RANGE[1]):
        try:
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                show_error=True,
                theme=gr.themes.Soft(),
                css=".message { min-height: 120px; }",
            )
            return
        except OSError as e:
            if "10048" in str(e) or "address already in use" in str(e).lower() or "bind" in str(e).lower():
                logger.warning("端口 %s 已被占用，尝试下一端口: %s", port, e)
                continue
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
