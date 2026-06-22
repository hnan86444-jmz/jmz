# type: ignore
"""MCP client helpers for the orchestrator and its local CLI."""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import click
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, ReadResourceResult

from .utils import get_mcp_server_config, get_openai_env_vars

logger = logging.getLogger(__name__)


@asynccontextmanager
async def init_session(host: str, port: int, transport: str):
    """Create an MCP client session over SSE or stdio."""

    if transport == "sse":
        url = f"http://{host}:{port}/sse"
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream, write_stream=write_stream
            ) as session:
                await session.initialize()
                logger.debug("SSE ClientSession initialized.")
                yield session
    elif transport == "stdio":
        env = dict(os.environ)
        try:
            env.update(get_openai_env_vars())
        except ValueError:
            logger.info(
                "OPENAI_* environment variables are not available; continuing because some MCP tools do not require them."
            )
        stdio_params = StdioServerParameters(
            command="uv",
            args=["run", "a2a-mcp"],
            env=env,
        )
        async with stdio_client(stdio_params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream=read_stream, write_stream=write_stream
            ) as session:
                await session.initialize()
                logger.debug("STDIO ClientSession initialized.")
                yield session
    else:
        raise ValueError(f"Unsupported transport: {transport}. Use 'sse' or 'stdio'.")


async def find_agent(session: ClientSession, query: str) -> CallToolResult:
    """Call the MCP find_agent tool."""

    logger.info("Calling 'find_agent' with query: %s...", query[:50])
    return await session.call_tool(
        name="find_agent",
        arguments={"query": query},
    )


async def find_resource(
    session: ClientSession, resource: str
) -> ReadResourceResult:
    """Read an MCP resource such as resource://agent_cards/planner_agent."""

    logger.info("Reading resource: %s", resource)
    return await session.read_resource(resource)


async def call_tool(
    session: ClientSession,
    tool_name: str,
    arguments: dict | None = None,
) -> CallToolResult:
    """Call any MCP tool with optional JSON arguments."""

    logger.info("Calling tool %s with arguments: %s", tool_name, arguments or {})
    return await session.call_tool(name=tool_name, arguments=arguments or {})


def dump_resource(result: ReadResourceResult) -> None:
    """Log MCP resource contents for CLI debugging."""

    logger.info("----- Resource Dump Start -----")
    logger.info("URI: %s", result.uri)
    if not result.contents:
        logger.warning("Resource has no contents.")
        logger.info("----- Resource Dump End -----")
        return
    for idx, content in enumerate(result.contents):
        logger.info("Content[%s] mimeType=%s", idx, getattr(content, "mimeType", None))
        if hasattr(content, "text") and content.text:
            try:
                data = json.loads(content.text)
                logger.info("%s", json.dumps(data, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                logger.info("%s", content.text)
    logger.info("----- Resource Dump End -----")


def dump_tool_result(result: CallToolResult) -> None:
    """Log MCP tool results for CLI debugging."""

    logger.info("----- Tool Result Start -----")
    if not getattr(result, "content", None):
        logger.warning("Tool result has no content.")
        logger.info("----- Tool Result End -----")
        return
    for idx, content in enumerate(result.content):
        text = getattr(content, "text", None)
        if text:
            try:
                data = json.loads(text)
                logger.info("Content[%s]: %s", idx, json.dumps(data, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                logger.info("Content[%s]: %s", idx, text)
    logger.info("----- Tool Result End -----")


async def _main(
    host: str,
    port: int,
    transport: str,
    query: str | None,
    resource: str | None,
    tool_name: str | None,
    tool_args: str | None,
) -> None:
    async with init_session(host, port, transport) as session:
        if query:
            try:
                result = await find_agent(session, query)
                if not getattr(result, "content", None) or not result.content:
                    logger.warning("find_agent returned no content")
                else:
                    data = json.loads(result.content[0].text)
                    logger.info("%s", json.dumps(data, indent=2))
            except Exception as e:
                logger.error("find_agent error: %s", e, exc_info=True)
        if resource:
            try:
                result = await find_resource(session, resource)
                logger.info("Resource metadata: %s", result)
                dump_resource(result)
            except Exception as e:
                logger.error("find_resource error: %s", e, exc_info=True)
        if tool_name:
            logger.info(
                "Running tool %s from CLI.",
                tool_name,
            )
            try:
                parsed_args = json.loads(tool_args) if tool_args else {}
                if not isinstance(parsed_args, dict):
                    raise ValueError("tool_args must decode to a JSON object.")
                result = await call_tool(session, tool_name, parsed_args)
                dump_tool_result(result)
            except Exception as e:
                logger.error("tool call error: %s", e, exc_info=True)


@click.command()
@click.option(
    "--host",
    default=None,
    help="SSE host; defaults to MCP_HOST when transport is sse",
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="SSE port; defaults to MCP_PORT when transport is sse",
)
@click.option(
    "--transport",
    default=None,
    type=click.Choice(["sse", "stdio"]),
    help="MCP transport; defaults to MCP_TRANSPORT",
)
@click.option("--find_agent", "query", help="Query to find an agent")
@click.option("--resource", help="Resource URI, e.g. resource://agent_cards/list")
@click.option(
    "--tool_name",
    help="Tool to run (optional), e.g. search_flights",
)
@click.option(
    "--tool_args",
    help='JSON object with tool arguments, e.g. {"origin":"TNA","destination":"PEK"}',
)
def cli(
    host: str | None,
    port: int | None,
    transport: str | None,
    query: str | None,
    resource: str | None,
    tool_name: str | None,
    tool_args: str | None,
) -> None:
    if transport is None or (transport == "sse" and (host is None or port is None)):
        config = get_mcp_server_config()
        transport = transport or config.transport
        if transport == "sse":
            host = host or config.host
            port = port if port is not None else config.port

    if transport is None:
        raise click.ClickException(
            "MCP transport is required. Set MCP_TRANSPORT or pass --transport."
        )
    if transport == "sse" and (host is None or port is None):
        raise click.ClickException(
            "SSE transport requires --host/--port or MCP_HOST/MCP_PORT/MCP_TRANSPORT."
        )

    asyncio.run(
        _main(
            host or "",
            port if port is not None else 0,
            transport,
            query,
            resource,
            tool_name,
            tool_args,
        )
    )


if __name__ == "__main__":
    cli()
