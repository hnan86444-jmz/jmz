# type: ignore
"""
Agent 服务入口：加载 agent card JSON，实例化对应 Agent（Orchestrator、Planner 或三种 Travel 之一），
并启动 A2A Starlette 应用。
从仓库根目录运行：uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/xxx.json --port N
"""
import json
import logging
import sys

from pathlib import Path

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCard
from a2a_mcp.agents import (
    OrchestratorAgent,
    LangGraphPlannerAgent,
    AirTicketingAgent,
    HotelBookingAgent,
    CarRentalAgent,
)
from a2a_mcp.common.agent_executor import GenericAgentExecutor


logger = logging.getLogger(__name__)


def get_agent(agent_card: AgentCard):
    """根据 agent_card.name 实例化对应 Agent（各 Agent 独立子包，互不共享）。"""
    try:
        if agent_card.name == 'Orchestrator Agent':
            return OrchestratorAgent()
        if agent_card.name == 'Langraph Planner Agent':
            return LangGraphPlannerAgent()
        if agent_card.name == 'Air Ticketing Agent':
            return AirTicketingAgent()
        if agent_card.name == 'Hotel Booking Agent':
            return HotelBookingAgent()
        if agent_card.name == 'Car Rental Agent':
            return CarRentalAgent()
        raise ValueError(
            f"Unknown agent name: {agent_card.name!r}. Expected one of: "
            "Orchestrator Agent, Langraph Planner Agent, Air Ticketing Agent, "
            "Hotel Booking Agent, Car Rental Agent."
        )
    except ValueError:
        raise
    except Exception as e:
        raise e


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10101)
@click.option('--agent-card', 'agent_card')
def main(host, port, agent_card):
    """启动 A2A HTTP 服务：加载 agent card、挂接 GenericAgentExecutor、运行 uvicorn。"""
    agent_card_path = agent_card
    try:
        if not agent_card_path:
            raise ValueError("Agent card is required")
        with Path(agent_card_path).open(encoding="utf-8") as file:
            data = json.load(file)
        agent_card = AgentCard(**data)

        client = httpx.AsyncClient()
        push_notification_config_store = InMemoryPushNotificationConfigStore()
        push_notification_sender = BasePushNotificationSender(
            client, config_store=push_notification_config_store
        )

        request_handler = DefaultRequestHandler(
            agent_executor=GenericAgentExecutor(agent=get_agent(agent_card)),
            task_store=InMemoryTaskStore(),
            push_config_store=push_notification_config_store,
            push_sender=push_notification_sender,
        )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(f'Starting server on {host}:{port}')

        uvicorn.run(server.build(), host=host, port=port)
    except FileNotFoundError:
        logger.error("Error: File '%s' not found.", agent_card_path)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Error: File '%s' contains invalid JSON.", agent_card_path)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during server startup: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()
