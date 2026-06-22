# -*- coding: utf-8 -*-
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path


def pick_answer(question: str) -> str:
    q = (question or "").strip()
    q_low = q.lower()

    full_spec = (
        "出发地：济南（遥墙国际机场 TNA）；"
        "目的地：北京（Beijing，首都机场 PEK / 大兴机场 PKX）；"
        "出发 2026-04-01，返程 2026-04-08；"
        "1人；预算 20000 RMB 内；经济舱；"
        "酒店：北京市中心（东城/西城/朝阳核心区）4星左右含早餐。"
    )

    if ("出发日期" in q and "返回日期" in q) or (
        "departure date" in q_low and "return" in q_low
    ):
        return full_spec

    if any(
        k in q_low
        for k in [
            "origin city",
            "trip origin",
            "where will you be traveling from",
            "traveling from",
            "destination",
            "destination city",
            "traveling to",
            "departure city",
            "preferred airport",
            "start date",
            "return date",
        ]
    ):
        return full_spec

    if (
        any(k in q for k in ["从哪个城市出发", "出发城市", "出发地", "出发城市是", "从哪里出发"])
        or "departure city" in q_low
        or "origin city" in q_low
        or "traveling from" in q_low
        or "where will you be traveling from" in q_low
        or "trip origin" in q_low
    ):
        return "济南（遥墙国际机场 TNA）"

    if (
        any(k in q for k in ["目的地", "去哪", "到哪个城市", "到哪里", "目的城市"])
        or "destination" in q_low
        or "destination city" in q_low
        or "traveling to" in q_low
    ):
        return "北京（Beijing，首都机场 PEK / 大兴机场 PKX）"

    if (
        any(k in q for k in ["出发日期", "什么时候出发", "出发时间", "几号出发", "开始日期"])
        or "departure date" in q_low
        or "start date" in q_low
    ):
        return "2026-04-01"

    if (
        any(k in q for k in ["返程日期", "返回日期", "什么时候回来", "回程时间", "几号回来", "结束日期"])
        or "return date" in q_low
        or "end date" in q_low
    ):
        return "2026-04-08"

    if any(k in q for k in ["几天", "天数", "住几晚", "行程时长"]) or "duration" in q_low:
        return "7天（6晚）"

    if (
        any(k in q for k in ["人数", "几个人", "旅客", "出行人数", "同行"])
        or "passengers" in q_low
        or "travelers" in q_low
    ):
        return "1人"

    if any(k in q for k in ["预算", "价格范围", "预算上限", "花费", "费用"]) or "budget" in q_low:
        return "总预算 20000 人民币以内（机票+酒店），优先性价比"

    if any(k in q for k in ["舱位", "经济舱", "商务舱", "头等舱"]) or "cabin" in q_low:
        return "经济舱即可"

    if any(k in q for k in ["中转", "直飞", "航班偏好"]) or "layover" in q_low:
        return "可接受 0-1 次中转，优先直飞或总时长合理的方案"

    if any(k in q for k in ["酒店", "住宿", "房型", "星级", "位置", "区域"]) or "hotel" in q_low:
        return "北京市中心（东城/西城/朝阳核心区）4星左右，含早餐，安静安全，方便地铁出行"

    if any(k in q for k in ["入住", "check-in"]) and any(k in q for k in ["退房", "check-out"]):
        return "入住 2026-04-01，退房 2026-04-08"

    if any(k in q for k in ["姓名", "乘客姓名", "旅客姓名"]) or "name" in q_low:
        return "张三（示例）"

    if any(k in q for k in ["护照", "证件号码", "证件号", "passport"]):
        return "中国境内出行，使用身份证即可，无需护照"

    if any(k in q for k in ["手机号", "电话", "联系方式"]) or "phone" in q_low:
        return "13800000000（示例）"

    if any(k in q for k in ["是否需要签证", "签证", "visa"]) or "visa" in q_low:
        return "中国境内出行，无需签证"

    return full_spec


async def run_until_done() -> dict:
    from a2a_mcp.agents.orchestrator.agent import OrchestratorAgent

    context_id = "auto_ctx"
    task_id = "auto_task"
    agent = OrchestratorAgent()

    transcript: list[dict] = []
    user_msg = "帮我规划济南去北京的行程并订机票酒店"
    max_turns = int(os.getenv("A2A_AUTO_TURNS", "20"))

    for turn in range(max_turns):
        final_dict: dict | None = None
        async for item in agent.stream(user_msg, context_id, task_id):
            if isinstance(item, dict) and "content" in item:
                transcript.append(
                    {
                        "turn": turn,
                        "from": "agent",
                        "require_user_input": bool(item.get("require_user_input")),
                        "is_task_complete": bool(item.get("is_task_complete")),
                        "response_type": item.get("response_type"),
                        "content": item.get("content"),
                    }
                )
                if item.get("require_user_input") or item.get("is_task_complete"):
                    final_dict = item
                    break

        if not final_dict:
            transcript.append(
                {
                    "turn": turn,
                    "from": "system",
                    "error": "No final dict produced in this turn",
                }
            )
            break

        if final_dict.get("is_task_complete"):
            return {"status": "completed", "transcript": transcript, "final": final_dict}

        if final_dict.get("require_user_input"):
            q = final_dict.get("content") or ""
            if not isinstance(q, str):
                q = str(q)
            answer = pick_answer(q)
            transcript.append(
                {
                    "turn": turn,
                    "from": "user",
                    "content": answer,
                }
            )
            user_msg = answer
            continue

    return {"status": "stopped", "transcript": transcript}


async def main() -> None:
    result = await run_until_done()
    out_dir = Path(__file__).resolve().parent.parent / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"auto_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    asyncio.run(main())

