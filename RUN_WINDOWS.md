# Windows 运行指南

## 前置要求

1. **安装 uv** (Python 包管理器)
   ```powershell
   # 使用 pip 安装
   pip install uv
   
   # 或者使用 PowerShell 脚本安装
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Python 3.11+** (项目要求 Python >= 3.11)

3. **OpenAI 兼容 API Key**（例如 SiliconFlow/OpenAI/自建兼容网关）

## 快速开始

### 步骤 1: 创建环境变量文件

在项目根目录创建 `.env` 文件，内容如下：

```env
OPENAI_API_KEY=your_openai_compatible_api_key_here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
# 可选环境变量
# LITELLM_MODEL=Qwen/Qwen2.5-7B-Instruct
# A2A_LOG_LEVEL=INFO
```

**重要**: 将 `your_openai_compatible_api_key_here` 替换为你的实际 Key。

### 步骤 2: 安装依赖并运行

有两种方式运行项目：

#### 方式 1: 使用自动化脚本（推荐）

运行 PowerShell 脚本：

```powershell
.\run.ps1
```

这个脚本会自动：
- 创建虚拟环境
- 安装依赖
- 启动所有服务（MCP Server + 5个Agent）
- 运行客户端测试
- 清理后台进程

#### 方式 2: 手动运行（分步执行）

> **说明**：使用 Gradio 前端时，编排器（Orchestrator）在 Gradio 进程内运行，**无需**单独启动 2.3 的 Orchestrator 服务。若仅做 CLI 测试，可跳过 2.9。

**2.1 创建虚拟环境并安装依赖**

```powershell
cd c:\Users\24514\Desktop\mcp-server-demo\a2a_mcp
uv venv
.\.venv\Scripts\Activate.ps1
```

**2.2 启动 MCP Server** (终端 1)

```powershell
uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
```

**2.3 启动 Orchestrator Agent** (终端 2，**可选**；使用 Gradio 时可跳过，编排器在 Gradio 进程内运行)

```powershell
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/orchestrator_agent.json --port 10101
```

**2.4 启动 Planner Agent** (终端 3)

```powershell
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/planner_agent.json --port 10102
```

**2.5 启动 Air Ticketing Agent** (终端 4)

```powershell
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/air_ticketing_agent.json --port 10103
```

**2.6 启动 Hotel Booking Agent** (终端 5)

```powershell
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/hotel_booking_agent.json --port 10104
```

**2.7 启动 Car Rental Agent** (终端 6)

```powershell
uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/car_rental_agent.json --port 10105
```

**2.8 运行客户端测试** (终端 7)

等待所有服务启动后（约10秒），运行：

```powershell
uv run --env-file .env python -m a2a_mcp.agents.orchestrator.mcp_client --resource "resource://agent_cards/list" --find_agent "I would like to plan a trip to France."
```

**2.9 启动 Gradio 前端** (终端 8)

```powershell
uv run --env-file .env python -m a2a_mcp.gradio_app
# 或：uv run --env-file .env a2a-mcp-ui
```

浏览器打开：http://localhost:7860

**Gradio 界面**：点击「发送」后，输入会立即出现在对话框并清空输入框；等待回复时显示「思考中...」。端口 7860 被占用时自动尝试 7861–7870，也可通过环境变量 `GRADIO_SERVER_PORT` 指定。

## 端口说明

- **10100**: MCP Server
- **10101**: Orchestrator Agent（使用 Gradio 时无需单独启动，编排器在 Gradio 进程内运行）
- **10102**: Planner Agent
- **10103**: Air Ticketing Agent
- **10104**: Hotel Booking Agent
- **10105**: Car Rental Agent
- **7860**: Gradio Web UI（Orchestrator in-process）

确保这些端口没有被其他程序占用。

## 故障排除

1. **如果 uv 命令未找到**
   - 确保已安装 uv 并添加到 PATH
   - 尝试使用完整路径或重新安装

2. **如果 OPENAI_API_KEY 错误**
   - 检查 `.env` 文件是否存在
   - 确认 API Key 格式正确
   - 确保 API Key 有足够的权限

3. **如果端口被占用**
   - 修改脚本中的端口号
   - 或关闭占用端口的程序

4. **如果依赖安装失败**
   - 确保 Python 版本 >= 3.11
   - 尝试更新 uv: `pip install --upgrade uv`

## 项目结构

- `agent_cards/`: Agent 配置文件（JSON 格式）
- `src/a2a_mcp/`: 源代码
  - `gradio_app.py`: Gradio Web 前端，编排器在进程内运行
  - `agents/`: 各 Agent 实现（orchestrator、planner、air_ticketing、hotel_booking、car_rental）
  - `common/`: 共享组件（MCP 服务 `mcp_server.py`、基类、工具等）
- `travel_agency.db`: SQLite 数据库（包含演示数据）
