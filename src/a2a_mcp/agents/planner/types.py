# type: ignore
"""Planner Agent 专用类型，不与其他 agent 共享。"""
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PlannerTask(BaseModel):
    """Planner 生成的单条任务。"""

    id: int = Field(description="任务顺序 ID。")
    description: str = Field(description="要执行的任务的清晰描述。")
    status: (
        Any
        | Literal[
            "input_required",
            "completed",
            "error",
            "pending",
            "incomplete",
            "todo",
            "not_started",
        ]
        | None
    ) = Field(description="任务状态", default="input_required")


class TripInfo(BaseModel):
    """行程信息。"""

    total_budget: str | None = Field(description="行程总预算")
    origin: str | None = Field(description="出发地")
    destination: str | None = Field(description="目的地")
    type: str | None = Field(description="行程类型：商务或休闲")
    start_date: str | None = Field(description="行程开始日期")
    end_date: str | None = Field(description="行程结束日期")
    travel_class: str | None = Field(
        description="舱位/座位等级：头等、商务或经济"
    )
    accommodation_type: str | None = Field(
        description="住宿类型：豪华酒店、经济酒店、AirBnB 等"
    )
    room_type: str | None = Field(description="房型：套房、单人间、双人间等")
    is_car_rental_required: str | None = Field(description="行程是否需要租车")
    type_of_car: str | None = Field(description="车型：SUV、轿车、卡车等")
    no_of_travellers: str | None = Field(description="出行人数")
    checkin_date: str | None = Field(description="酒店入住日期")
    checkout_date: str | None = Field(description="酒店退房日期")
    car_rental_start_date: str | None = Field(description="租车开始日期")
    car_rental_end_date: str | None = Field(description="租车结束日期")

    @model_validator(mode="before")
    @classmethod
    def set_dependent_var(cls, values):
        """Pydantic 依赖字段设置。"""
        if isinstance(values, dict) and "start_date" in values:
            values["checkin_date"] = values["start_date"]
        if isinstance(values, dict) and "end_date" in values:
            values["checkout_date"] = values["end_date"]
        if isinstance(values, dict) and "start_date" in values:
            values["car_rental_start_date"] = values["start_date"]
        if isinstance(values, dict) and "end_date" in values:
            values["car_rental_end_date"] = values["end_date"]
        return values


class TaskList(BaseModel):
    """Planner Agent 的输出 schema。"""

    original_query: str | None = Field(description="原始用户查询，用于上下文。")
    trip_info: TripInfo | None = Field(description="行程信息")
    tasks: list[PlannerTask] = Field(description="按顺序执行的任务列表。")


class ResponseFormat(BaseModel):
    """LLM 结构化输出：status、question、以及 TaskList 的 content。"""

    status: Literal["input_required", "completed", "error"] = "input_required"
    question: str = Field(description="生成计划所需用户输入")
    content: TaskList | None = Field(description="计划生成时的任务列表", default=None)
