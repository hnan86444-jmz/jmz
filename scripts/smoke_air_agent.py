# -*- coding: utf-8 -*-
import asyncio
import json

import httpx
from a2a.client import A2AClient
from a2a.types import AgentCard, MessageSendParams, SendStreamingMessageRequest, TaskState


async def main() -> None:
    card = AgentCard(
        **json.loads(open("agent_cards/air_ticketing_agent.json", "r", encoding="utf-8").read())
    )
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        a2a = A2AClient(client, card)
        req = SendStreamingMessageRequest(
            id="1",
            params=MessageSendParams(
                message={
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "帮我订 2026-04-01 从济南到北京的机票，1人，经济舱，优先直飞",
                        }
                    ],
                    "messageId": "m1",
                    "contextId": "ctx1",
                }
            ),
        )
        async for chunk in a2a.send_message_streaming(req):
            if hasattr(chunk, "root") and hasattr(chunk.root, "result") and hasattr(chunk.root.result, "status"):
                st = chunk.root.result.status.state
                if st in (TaskState.completed, TaskState.input_required, TaskState.failed):
                    print("final_state", st)
                    break


if __name__ == "__main__":
    asyncio.run(main())

