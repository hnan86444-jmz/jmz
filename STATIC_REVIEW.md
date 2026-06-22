# 静态核查说明

本文档记录对核心代码的静态核查结果与修改，确保逻辑清晰、类型一致、边界安全。

## 核查范围

- `src/a2a_mcp/agents/orchestrator/orchestration.py` — 编排图与 A2A 调用（编排器自包含）
- `src/a2a_mcp/agents/orchestrator/` — 编排器入口、摘要与自动回答
- `src/a2a_mcp/agents/planner/` — 规划器图与结构化输出
- `src/a2a_mcp/agents/air_ticketing/`、`hotel_booking/`、`car_rental/` — 各任务 Agent 独立实现
- `src/a2a_mcp/common/agent_executor.py` — A2A 与 agent.stream 桥接
- `src/a2a_mcp/agents/__main__.py` — 入口与 Agent 卡加载
- `src/a2a_mcp/common/mcp_server.py` — MCP 服务（资源与工具）；编排器 MCP 客户端在 `agents/orchestrator/mcp_client.py`

## 已修复问题

### 1. MCP Server (`common/mcp_server.py`)

- **find_agent 嵌入向量**：`query_embedding` 已是 `response.data[0].embedding` 的列表，不应再取 `query_embedding['embedding']`，否则会报错。已改为直接使用 `query_embedding`。
- **load_agent_cards 返回值**：目录不存在时原返回 `agent_cards`，与类型注解 `tuple[list[str], list[dict]]` 不一致。已改为返回 `(card_uris, agent_cards)`。
- **query_travel_data 异常**：`'no such column' in e` 中 `e` 为 Exception，应使用 `str(e)` 判断；`return {'error': {e}}` 应返回可序列化字符串。已改为 `err_msg = str(e)` 并统一用 `err_msg` 判断与返回。

### 2. Agent 入口 (`agents/__main__.py`)

- **Path.open 用法**：`Path.open(agent_card)` 错误，`Path.open` 为实例方法。已改为 `Path(agent_card).open(encoding="utf-8")`。

### 3. Agent Executor (`common/agent_executor.py`)

- **dict 键安全**：对 `item['is_task_complete']`、`item['response_type']`、`item['content']` 使用 `.get()`，避免 KeyError；对非 dict 的 yield 更稳健。
- **content 类型**：`response_type == 'data'` 时 content 可能为 dict，已统一用 `item.get('content', '')` 并在 TextPart 时做 `str(content)` 保护。

### 4. Orchestrator Agent (`agents/orchestrator/`)

- **OpenAI 调用方式**：统一使用 `init_api_key()` 返回的 client，与项目其他处一致（base_url、API key）。
- **Chat API**：由 `client.ChatCompletion.create` 改为 `client.chat.completions.create`，与当前 OpenAI 客户端一致。
- **响应内容读取**：使用 `getattr(msg, "content", None)` 并做 `isinstance(content, str)` 判断，避免因 message 结构变化导致异常。
- **answer_user_question**：去掉无效的 `response_mime_type`，改为 `response_format={"type": "json_object"}`；模型从环境变量 `LITELLM_MODEL` 读取，与 Planner/Travel 一致。

### 5. 任务 Agent（`agents/air_ticketing/`、`hotel_booking/`、`car_rental/`）

- **首条 yield 字段**：首条进度信息增加 `"response_type": "text"`，与 executor 中对 `response_type` 的期望一致，避免 KeyError。

## 逻辑与注释补充

- **orchestration**（`agents/orchestrator/orchestration.py`）：在 planner 解析 artifact 处注明 A2A 中 artifact 结构（name、parts[0].root.data 为 TaskList 字典）。
- **orchestrator**：在 stream 主循环注明「跑图直至 END」「用本地镜像做 answer_user_question / generate_summary」「暂停时尝试自动回答」「无 planned_tasks 时仍标记 done 并生成 summary」。
- **agent_executor**：注明 stream 中 item 可能为 A2A chunk 或我们自己的 dict。
- **planner**：在 get_agent_response 注明 config 需含 `configurable.thread_id` 以便 get_state 取到正确状态。

## 数据流与约定（供后续维护）

1. **Orchestrator stream**  
   - 用 `_state` 保存 LangGraph 状态；每次用户消息先 append 到 `query_history`，再初始化或更新 `_state`；若上一轮 paused，本轮将 `user_query` 视为用户/自动回答并设 `resume_current_task`。
2. **Planner artifact**  
   - Executor 以 `add_artifact(..., name=f'{agent_name}-result')` 上报，编排侧用 `artifact.name == "PlannerAgent-result"` 与 `parts[0].root.data`（TaskList 字典）解析。
3. **Executor 与 agent.stream**  
   - 若 item 有 `root` 且为 `SendStreamingMessageSuccessResponse`，按 A2A 事件转发；否则按 dict 处理 `is_task_complete`、`require_user_input`、`response_type`、`content`。
4. **Agent 卡名称**  
   - `__main__.py` 中与 `agent_card.name` 匹配的字符串需与各 `agent_cards/*.json` 的 `"name"` 一致（如 `"Langraph Planner Agent"`）。

## 建议后续检查

- 各 agent_cards/*.json 的 `name` 与 `get_agent()` 分支完全一致。
- MCP 资源 `resource://agent_cards/planner_agent` 返回的 JSON 结构（含 `agent_card` 数组）与 `_get_planner_card` 的解析一致。
- 若使用异步 OpenAI 客户端，可将 `generate_summary` 内同步 `chat.completions.create` 改为异步调用，避免阻塞事件循环。
