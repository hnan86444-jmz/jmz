# type: ignore
"""
酒店 Agent 专用 MCP 客户端：用于直接调用 MCP 工具/资源（可选）。

说明：
- 任务执行时仍可通过 langchain_mcp_adapters.load_mcp_tools 自动加载全部 MCP 工具；
- 该模块提供“直接 call_tool/read_resource”的能力，方便后续使用更多 MCP 工具。
"""
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, ReadResourceResult

from .utils import get_mcp_server_config, get_openai_env_vars

logger = logging.getLogger(__name__)


@asynccontextmanager
async def init_session(host: str, port: int, transport: str):
    """创建 MCP ClientSession：SSE（url=http://host:port/sse）或 stdio。"""
    if transport == "sse":
        url = f"http://{host}:{port}/sse"
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream, write_stream=write_stream
            ) as session:
                await session.initialize()
                yield session
    elif transport == "stdio":
        stdio_params = StdioServerParameters(
            command="uv",
            args=["run", "a2a-mcp"],
            env=get_openai_env_vars(),
        )
        async with stdio_client(stdio_params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream, write_stream=write_stream
            ) as session:
                await session.initialize()
                yield session
    else:
        raise ValueError(f"Unsupported transport: {transport}. Use 'sse' or 'stdio'.")


@asynccontextmanager
async def init_default_session():
    """使用本 agent 的 MCP 配置建立会话。"""
    cfg = get_mcp_server_config()
    async with init_session(cfg.host, cfg.port, cfg.transport) as session:
        yield session


async def call_tool(
    session: ClientSession, name: str, arguments: dict[str, Any] | None = None
) -> CallToolResult:
    """直接调用任意 MCP 工具。"""
    return await session.call_tool(name=name, arguments=arguments or {})


async def read_resource(session: ClientSession, uri: str) -> ReadResourceResult:
    """读取 MCP 资源（如 resource://agent_cards/list）。"""
    return await session.read_resource(uri)


def parse_tool_text_json(result: CallToolResult) -> Any:
    """将 MCP tool 的 text 内容解析为 JSON（若可解析）。"""
    if not getattr(result, "content", None) or not result.content:
        return None
    text = getattr(result.content[0], "text", None)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text

