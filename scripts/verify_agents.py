#!/usr/bin/env python3
"""
核实拆分后 Agent 逻辑：导入、实例化、接口一致性。
从项目根目录运行：uv run python scripts/verify_agents.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 确保可导入 a2a_mcp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    errors = []

    # 1. 导入（各 Agent 独立子包）
    try:
        from a2a_mcp.agents import (
            OrchestratorAgent,
            LangGraphPlannerAgent,
            AirTicketingAgent,
            HotelBookingAgent,
            CarRentalAgent,
        )
        from a2a_mcp.agents.air_ticketing import AirTicketingAgent as A2
        from a2a_mcp.agents.hotel_booking import HotelBookingAgent as H2
        from a2a_mcp.agents.car_rental import CarRentalAgent as C2
        assert AirTicketingAgent is A2 and HotelBookingAgent is H2 and CarRentalAgent is C2
        print("  [OK] 导入 agents 包及子包一致")
    except Exception as e:
        errors.append(f"导入失败: {e}")
        print(f"  [FAIL] 导入: {e}")
        return 1

    # 2. 实例化（不依赖 MCP/LLM 的构造）
    orch = plan = air = hotel = car = None
    try:
        orch = OrchestratorAgent()
        assert hasattr(orch, "stream") and hasattr(orch, "agent_name")
        assert orch.agent_name == "Orchestrator Agent"
        print("  [OK] OrchestratorAgent 实例化及属性")
    except Exception as e:
        errors.append(f"OrchestratorAgent: {e}")
        print(f"  [FAIL] OrchestratorAgent: {e}")

    try:
        plan = LangGraphPlannerAgent()
        assert hasattr(plan, "stream") and hasattr(plan, "agent_name")
        assert plan.agent_name == "PlannerAgent"
        print("  [OK] LangGraphPlannerAgent 实例化及属性")
    except Exception as e:
        errors.append(f"LangGraphPlannerAgent: {e}")
        print(f"  [FAIL] LangGraphPlannerAgent: {e}")

    try:
        air = AirTicketingAgent()
        assert hasattr(air, "stream") and hasattr(air, "agent_name")
        assert air.agent_name == "AirTicketingAgent"
        print("  [OK] AirTicketingAgent 实例化及属性")
    except Exception as e:
        errors.append(f"AirTicketingAgent: {e}")
        print(f"  [FAIL] AirTicketingAgent: {e}")

    try:
        hotel = HotelBookingAgent()
        assert hasattr(hotel, "stream") and hasattr(hotel, "agent_name")
        assert hotel.agent_name == "HotelBookingAgent"
        print("  [OK] HotelBookingAgent 实例化及属性")
    except Exception as e:
        errors.append(f"HotelBookingAgent: {e}")
        print(f"  [FAIL] HotelBookingAgent: {e}")

    try:
        car = CarRentalAgent()
        assert hasattr(car, "stream") and hasattr(car, "agent_name")
        assert car.agent_name == "CarRentalBookingAgent"
        print("  [OK] CarRentalAgent 实例化及属性")
    except Exception as e:
        errors.append(f"CarRentalAgent: {e}")
        print(f"  [FAIL] CarRentalAgent: {e}")

    # 3. get_agent 与 agent card 名称匹配
    try:
        from a2a.types import AgentCard
        from a2a_mcp.agents.__main__ import get_agent

        cards_dir = Path(__file__).resolve().parent.parent / "agent_cards"
        if not cards_dir.is_dir():
            print("  [SKIP] 未找到 agent_cards 目录，跳过 get_agent 校验")
        else:
            for name, expected_type in [
                ("orchestrator_agent.json", OrchestratorAgent),
                ("planner_agent.json", LangGraphPlannerAgent),
                ("air_ticketing_agent.json", AirTicketingAgent),
                ("hotel_booking_agent.json", HotelBookingAgent),
                ("car_rental_agent.json", CarRentalAgent),
            ]:
                p = cards_dir / name
                if not p.exists():
                    continue
                data = json.loads(p.read_text(encoding="utf-8"))
                card = AgentCard(**data)
                agent = get_agent(card)
                assert type(agent).__name__ == expected_type.__name__, f"{name}: got {type(agent).__name__}"
            print("  [OK] get_agent 与各 agent card 名称匹配")
    except Exception as e:
        errors.append(f"get_agent: {e}")
        print(f"  [FAIL] get_agent: {e}")

    # 4. Executor 与 agent 接口（仅对已成功实例化的 agent 检查）
    try:
        from a2a_mcp.common.agent_executor import GenericAgentExecutor
        from a2a_mcp.common.base_agent import BaseAgent

        agents_ok = [a for a in [orch, plan, air, hotel, car] if a is not None]
        for agent in agents_ok:
            assert isinstance(agent, BaseAgent)
            assert callable(getattr(agent, "stream", None))
            executor = GenericAgentExecutor(agent=agent)
            assert executor.agent is agent
        print("  [OK] GenericAgentExecutor 与各 Agent 接口一致")
    except Exception as e:
        errors.append(f"Executor 接口: {e}")
        print(f"  [FAIL] Executor 接口: {e}")

    if errors:
        print("\n核实未通过:", errors)
        return 1
    print("\n核实通过：拆分后逻辑通。")
    return 0


if __name__ == "__main__":
    exit(main())
