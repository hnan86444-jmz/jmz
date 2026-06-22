# A2A with MCP as Registry

**Leveraging Model Context Protocol (MCP) as a standardized mechanism for discovering and retrieving Google A2A Agent Cards, enabling dynamic agent interaction using A2A.**

## Table of Contents

- [A2A with MCP as Registry](#a2a-with-mcp-as-registry)
  - [Table of Contents](#table-of-contents)
  - [Objective](#objective)
  - [Background](#background)
    - [A2A Protocol](#a2a-protocol)
    - [Model Context Protocol (MCP)](#model-context-protocol-mcp)
  - [Core Proposal](#core-proposal)
    - [Storing Agent Cards](#storing-agent-cards)
    - [Discovering Agents via MCP](#discovering-agents-via-mcp)
    - [Retrieving Agent Cards](#retrieving-agent-cards)
    - [Finding an Agent for a Task](#finding-an-agent-for-a-task)
    - [Initiating A2A Communication](#initiating-a2a-communication)
  - [Use Case: Orchestrated Task Execution](#use-case-orchestrated-task-execution)
    - [Core Concepts](#core-concepts)
    - [Architectural Components](#architectural-components)
  - [Example Flow: Travel Agent](#example-flow-travel-agent)
  - [Steps to execute the example](#steps-to-execute-the-example)
    - [File/Directory Descriptions](#filedirectory-descriptions)
  - [Disclaimer](#disclaimer)

## Objective

To leverage Model Context Protocol (MCP) as a standardized mechanism for discovering and retrieving Google A2A Agent Cards. This enables dynamic agent interaction, particularly for planning and orchestration agents that utilize the A2A protocol.

## Background

### A2A Protocol

The Agent-to-Agent (A2A) protocol standardizes runtime communication between agents. It defines:

- **Agent Card:** A JSON schema describing an agent's identity, capabilities (actions/functions), and interaction endpoints.
- **Message Formats & Interaction Flows:** Such as `ExecuteTask` for direct agent-to-agent interaction.

### Model Context Protocol (MCP)

MCP defines a standard way for applications (including AI models) to discover, access, and utilize contextual information, referred to as "tools", "resources", etc.

## Core Proposal

The central idea is to use an MCP server as a centralized, queryable repository for A2A Agent Cards.

### Storing Agent Cards

- Each A2A Agent Card (JSON) is stored (e.g., as a JSON file).
- The MCP server exposes these Agent Cards as resources.
- The underlying storage system could be a file system, database or even a vector store. This example uses agent cards stored in a file system, generates embeddings and uses them to find matches.

### Discovering Agents via MCP

- Clients query the MCP server's resource API (`list_resources`) to discover available agent cards.
- Filtering can be applied using additional metadata (e.g., `streaming` support, tags like `currency conversion`), though not explicitly covered in this example.

### Retrieving Agent Cards

- The requesting agent uses resource URIs (obtained from discovery) to fetch the full JSON Agent Card(s) via the MCP server API.

### Finding an Agent for a Task

- Requesting agents can use tools exposed on the MCP server to find the most relevant agent for a specific query.

### Initiating A2A Communication

- Once Agent Card(s) are retrieved, the requesting agent uses them in an A2AClient.
- Agents (like a Planning Agent) needing collaborators then use the standard A2A protocol to communicate directly with target agents.
- MCP is not involved in this direct runtime interaction after discovery.

## Use Case: Orchestrated Task Execution

This system enables a workflow where specialized agents collaborate dynamically.

### Core Concepts

1. **Orchestration:** Planner and Executor agents manage the overall flow of a user query.
2. **Specialization:** Task Agents are experts in specific types of tasks.
3. **Dynamic Discovery:** The MCP Server allows for flexible addition, removal, or updates of Task Agents without modifying the Executor.
4. **Standardized Communication:** The A2A protocol ensures reliable inter-agent communication.

### Architectural Components

1. **User Interface (UI) / Application Gateway:** Entry point for user queries.
2. **Orchestrator Agent:**
   - Receives a structured plan from the Planner Agent.
   - Iterates through tasks.
   - For each task:
     - Queries the MCP Server for a suitable Task Agent based task (additionally capabilities).
     - Connects and sends task details to the Task Agent via A2A.
     - Receives results from the Task Agent via A2A.
     - Manages task state and errors.
   - Validates the results and potentially triggers replanning as needed.
   - Synthesizes, summarizes, and formats results into a coherent user response.
3. **Planner Agent:**
   - Receives the raw user query.
   - Decomposes the query into a structured plan of tasks (potentially a DAG), specifying required capabilities for each.
4. **Model Context Protocol (MCP) Server:**
   - Acts as a registry for Task Agents, hosting their Agent Cards.
   - Provides an interface for the Executor Agent to query for agents.
   - Provides an interface for the Executor Agent to query for tools.
5. **Task Agents (Pool/Fleet):**
   - Independent, specialized agents (e.g., Search Agent, Calculation Agent).
   - Expose A2A-compatible endpoints.
   - Execute tasks and return results to the Executor via A2A.
6. **A2A Communication Layer:** The underlying protocol for inter-agent communication.

```mermaid
flowchart LR
 subgraph s1["User Facing Layer"]
        UI["User Interface / Gateway"]
  end
 subgraph s3["Agent / Tool Discovery"]
        MCP["MCP Server (Agent / Tool Registry)"]
  end
 subgraph s4["Task Execution Layer"]
        T1["Task Agent 1 (e.g., Air Tickets)"]
        T2["Task Agent 2 (e.g., Hotel Reservation)"]
        T3["Task Agent N (e.g., Car Rental Reservation)"]
  end
    UI --> E["Orchestrator Agent"]
    E --> P["Planner Agent"] & MCP & A["Summary Agent"] & T1 & T2 & T3 & UI
    T2 --> E & MCP
    T3 --> E & MCP
    T1 --> MCP
     T1:::taskAgent
     T1:::Sky
     T2:::taskAgent
     T2:::Sky
     T3:::taskAgent
     T3:::Sky
    classDef taskAgent fill:#f9f,stroke:#333,stroke-width:2px
    classDef a2aLink stroke-width:2px,stroke:#0077cc,stroke-dasharray: 5 5
    classDef Sky stroke-width:1px, stroke-dasharray:none, stroke:#374D7C, fill:#E2EBFF, color:#374D7C
```

## Example Flow: Travel Agent

1. User requests a trip plan.
2. **Orchestrator Agent** receives the request.
   1. Looks up the **Planner Agent**'s card via MCP and connects.
   2. Invokes the Planner Agent to get a detailed plan.
   3. For each step in the plan:
      1. Invokes an MCP tool (e.g., `find_agent`) to fetch the Agent Card of the best Task Agent.
      2. Invokes the selected Task Agent via A2A to execute the task:
         - _Air Tickets:_ Task Agent will use a helper tool from the MCP server. The tool queries a SQLLite database to find the flights.
         - _Hotels:_ Task Agent will use a helper tool from the MCP server.
           The tool queries a SQLLite database to find the hotels.
         - _Car Rental:_ Task Agent will use a helper tool from the MCP server.
           The tool queries a SQLLite database to find the rental cars.
      3. Stores the results in memory
   4. Aggregates results and summarizes them for the client.
   5. If the agent discovers budget mismatch or failures in booking, a re-planning task is kicked off.

## Steps to execute the example

This sample is built with **LangGraph + MCP** throughout: the Orchestrator, Planner, and all Task Agents (Air Ticketing, Hotel Booking, Car Rental) use LangGraph. Each task agent lives in its own folder (`air_ticketing/`, `hotel_booking/`, `car_rental/`) with no shared implementation.

### Environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_compatible_api_key_here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
MCP_TRANSPORT=sse
MCP_HOST=localhost
MCP_PORT=10100
# Optional:
# LITELLM_MODEL=Qwen/Qwen2.5-7B-Instruct
# A2A_LOG_LEVEL=INFO
```

### Start services (recommended order)

> 使用 Gradio UI 时，编排器（Orchestrator）在 Gradio 进程内运行，**无需**单独启动 10101 端口的 Orchestrator 服务。
>
> Note (Windows PowerShell): 用 `;` 串联命令（不要用 `&&`）。

1. **MCP Server (10100)**

```bash
cd <project-root>
uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
```

2. **Planner (10102)**

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/planner_agent.json --port 10102
```

3. **Air Ticketing (10103)**

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/air_ticketing_agent.json --port 10103
```

4. **Hotel Booking (10104)**

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/hotel_booking_agent.json --port 10104
```

5. **Car Rental (10105)**

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/car_rental_agent.json --port 10105
```

6. **Gradio UI (7860)**（编排器在同一进程内运行，无需单独启动 Orchestrator 服务）

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.gradio_app
# 或: uv run --env-file .env a2a-mcp-ui
```

在浏览器打开 http://localhost:7860 进行对话。

**Gradio 界面说明**：
- 点击「发送」或按回车后，输入内容会**立即**出现在对话框，输入框清空
- 等待回复期间会显示「思考中...」，收到 Agent 回复后自动替换为完整内容
- 端口 7860 若被占用，会自动尝试 7861–7870；可通过环境变量 `GRADIO_SERVER_PORT` 指定端口

### Optional: start Orchestrator as an A2A server (10101)

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/orchestrator_agent.json --port 10101
```

### Optional: MCP CLI test

```bash
cd <project-root>
uv run --env-file .env python -m a2a_mcp.agents.orchestrator.mcp_client --resource "resource://agent_cards/list" --find_agent "I would like to plan a trip to France."
```


### File/Directory Descriptions

- **`agent_cards/`**: This directory stores the JSON schemas for each A2A Agent Card. These cards define the identity, capabilities, and endpoints of the different agents in the system. The MCP server serves these cards.

  - `*_agent.json`: Each JSON file represents a specific agent's card (e.g., `air_ticketing_agent.json` for the agent that handles flight bookings).

- **`src/a2a_mcp/`**: The primary Python source code for this A2A with MCP sample.

  - **`gradio_app.py`**: Gradio Web 前端，与编排器对话；编排器在本进程内实例化，通过 MCP 发现并调用各 Task Agent。使用生成器模式实现：点击发送后立即显示用户消息并清空输入框，等待回复时显示「思考中...」。
  - **`agents/`**: LangGraph-based agent implementations.
    - `__main__.py`: Main script to start up the agent services.
    - `air_ticketing/`: Air Ticketing Agent (LangGraph ReAct + MCP tools), independent implementation.
    - `hotel_booking/`: Hotel Booking Agent (LangGraph ReAct + MCP tools), independent implementation.
    - `car_rental/`: Car Rental Agent (LangGraph ReAct + MCP tools), independent implementation.
    - `planner/`: Planner Agent (custom LangGraph StateGraph) that breaks down user requests into structured plans.
    - `orchestrator/`: Orchestrator Agent (LangGraph StateGraph in `orchestrator/orchestration.py`) that coordinates the Planner and Task Agents via MCP and A2A.
  - **`common/`**: Shared infrastructure (base class, executor, utils).
    - `agent_executor.py`: A2A execution adapter (state, task execution, event queue).
    - `base_agent.py`: Base class for all agents.
    - `utils.py`: Utilities and MCP server config (ServerConfig, init_api_key). Each agent has its own prompts and types.
    - `mcp_server.py`: The MCP server implementation (agent cards + tools).

- **`travel_agency.db`**: A light weight SQLLite DB that hosts the demo data.

## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
