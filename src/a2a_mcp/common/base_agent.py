# type: ignore
"""Base agent 模型：所有 A2A Agent 共用的字段（agent_name、description、content_types）。"""
from abc import ABC

from pydantic import BaseModel, Field


class BaseAgent(BaseModel, ABC):
    """Orchestrator、Planner、Travel 等 Agent 的抽象基类，供 GenericAgentExecutor 使用。"""

    model_config = {
        'arbitrary_types_allowed': True,
        'extra': 'allow',
    }

    agent_name: str = Field(
        description='Agent 名称。',
    )

    description: str = Field(
        description='Agent 用途的简要描述。',
    )

    content_types: list[str] = Field(description='支持的内容类型。')
