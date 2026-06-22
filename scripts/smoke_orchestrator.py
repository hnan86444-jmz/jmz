# -*- coding: utf-8 -*-
import asyncio


async def main() -> None:
    from a2a_mcp.agents.orchestrator.agent import OrchestratorAgent

    agent = OrchestratorAgent()
    async for item in agent.stream("帮我规划去北京的行程并订机票酒店", "ctx", "task"):
        if isinstance(item, dict):
            need = bool(item.get("require_user_input"))
            done = bool(item.get("is_task_complete"))
            content = item.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            print("DICT", {"require_user_input": need, "is_task_complete": done})
            print("CONTENT", content[:200].replace("\n", "\\n"))
            if need or done:
                break


if __name__ == "__main__":
    asyncio.run(main())

