# 智能矿业日报系统

基于 LangGraph 和 MCP (Model Context Protocol) 的智能矿业日报生成系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Mining Agent (智能体)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LangGraph Workflow                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ 意图解析  │→│ 工具选择  │→│ 数据收集  │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  │  ┌──────────┐  ┌──────────┐                         │   │
│  │  │ 报告生成  │←│ 信息整理  │                         │   │
│  │  └──────────┘  └──────────┘                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓ 调用 MCP Tools
┌─────────────────────────────────────────────────────────────┐
│                     MCP Servers                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ News Server  │  │ Mining Data  │  │ Price Server │      │
│  │  (Port 8001) │  │  (Port 8002) │  │  (Port 8003) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓ 获取真实数据
┌─────────────────────────────────────────────────────────────┐
│                    数据源 (真实、可追溯)                       │
│  • RSS Feeds (Mining.com, Mining News, etc.)                │
│  • USGS Mineral Commodity Summaries 2024                    │
│  • Metals-API / Commodities-API                             │
│  • LME, S&P Global Platts, LBMA                             │
│  • Company ASX Announcements & Technical Reports            │
└─────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 智能体架构 (基于 LangGraph)
- **意图解析**: 使用 LLM 智能解析用户输入，理解查询意图
- **工具选择**: 根据意图自动选择合适的 MCP 工具
- **数据收集**: 自动调用 MCP 服务器获取真实数据
- **信息整理**: 使用 LLM 整理数据并生成结构化报告
- **文件输出**: 自动保存 Markdown 格式报告

### 2. 真实数据源
- **新闻数据**: 来自 Mining.com、Mining News 等真实 RSS feeds
- **储量数据**: 来自 USGS、JORC 等权威机构公开报告
- **价格数据**: 来自 Metals-API、LME、S&P Global 等市场数据源
- **来源追溯**: 每条数据都标注来源、链接和获取时间

### 3. 支持的查询类型
- **新闻查询**: "锂矿最新新闻"、"copper mining news"
- **储量查询**: "Pilbara地区锂矿储量"、"global lithium reserves"
- **价格查询**: "铜矿价格"、"iron ore price"
- **产量查询**: "全球锂矿产量"、"lithium production stats"
- **综合报告**: "生成Pilbara锂矿日报"、"comprehensive lithium report"

### 4. 支持的矿物类型
- Lithium (锂)
- Copper (铜)
- Iron (铁)
- Gold (金)
- Nickel (镍)

### 5. 支持的地区
- Global (全球)
- Pilbara (皮尔巴拉)
- Australia (澳大利亚)
- Chile (智利)
- China (中国)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
# ============================================================
# LLM (Large Language Model) Configuration
# ============================================================
# OpenAI API Key (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here

# OpenAI API Base URL (可选，默认官方)
# 支持第三方兼容API（DeepSeek、硅基流动等）
OPENAI_BASE_URL=https://api.openai.com/v1

# LLM Model (可选，默认 gpt-3.5-turbo)
# 支持: gpt-3.5-turbo, gpt-4, gpt-4o, deepseek-chat 等
OPENAI_MODEL=gpt-3.5-turbo

# ============================================================
# MCP Server URLs (可选，默认本地)
# ============================================================
MCP_NEWS_SERVER_URL=http://localhost:8001/mcp
MCP_MINING_SERVER_URL=http://localhost:8002/mcp
MCP_PRICE_SERVER_URL=http://localhost:8003/mcp

# ============================================================
# External Data API Keys (可选)
# ============================================================
METALS_API_KEY=your-metals-api-key-here
COMMODITIES_API_KEY=your-commodities-api-key-here
```

### 3. 启动系统

#### 方式一：使用启动脚本（推荐）
```bash
# Windows CMD
start.bat

# 或使用 PowerShell（更好的中文支持）
start.ps1
```

#### 方式二：Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 运行 Agent
docker exec -it mining-agent python agents/mining_agent.py
```

#### 方式三：手动启动
```bash
# 终端 1: 启动新闻服务器
python servers/news_server.py

# 终端 2: 启动储量数据服务器
python servers/mining_data_server.py

# 终端 3: 启动价格服务器
python servers/price_server.py

# 终端 4: 运行智能体
python agents/mining_agent.py
```

### 4. 使用示例

系统启动后，输入查询：

```
请输入您的查询: 生成Pilbara地区锂矿综合日报
```

系统将自动：
1. 解析查询意图
2. 收集新闻、储量、价格、产量数据
3. 生成结构化报告
4. 保存为 Markdown 文件

## 输出示例

```markdown
# Pilbara 地区锂矿日报

**生成时间**: 2024-01-15 10:30:00

## 📰 新闻摘要

### 1. Pilbara Minerals 宣布扩产计划
- **来源**: Mining.com
- **日期**: 2024-01-15
- **摘要**: Pilbara Minerals 计划将 Pilgangoora 项目产能提升至 100 万吨/年...

## 📊 储量数据

### 全球锂储量
- **总储量**: 26,000,000 吨 LCE
- **数据来源**: USGS Mineral Commodity Summaries 2024

### Pilbara 地区
- **Pilgangoora**: 2.12 亿吨 @ 1.25% Li2O
- **Wodgina**: 2.59 亿吨 @ 1.17% Li2O
...

## 💰 价格数据

- **当前价格**: $13,500 USD/吨
- **数据来源**: S&P Global Platts
- **更新时间**: 2024-01-15 09:00:00

## 📋 数据来源追溯

### 1. News 数据
- Mining.com
- Mining News
- **获取时间**: 2024-01-15T10:30:00

### 2. Reserves 数据
- **来源**: USGS Mineral Commodity Summaries 2024
- **链接**: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-lithium.pdf
- **获取时间**: 2024-01-15T10:30:05

...
```

## 项目结构

```
凌云智矿/
├── agents/
│   └── mining_agent.py          # 智能体主程序（基于 LangGraph）
├── servers/
│   ├── news_server.py           # 新闻 MCP 服务器 (端口 8001)
│   ├── mining_data_server.py    # 储量数据 MCP 服务器 (端口 8002)
│   └── price_server.py          # 价格 MCP 服务器 (端口 8003)
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量配置示例
├── .env                         # 实际环境变量文件（需创建）
├── docker-compose.yml           # Docker 编排配置
├── Dockerfile.server            # Server 端 Dockerfile
├── Dockerfile.agent             # Agent 端 Dockerfile
├── start.bat                    # 快速启动脚本
├── RUN.md                       # 快速启动指南
└── README.md                    # 详细使用说明
```

## 技术栈

- **LangGraph**: 智能体工作流编排
- **LangChain**: LLM 工具集成
- **MCP (Model Context Protocol)**: 服务器-客户端通信协议
- **FastMCP**: MCP 服务器实现
- **OpenAI GPT-3.5**: 意图解析和报告生成
- **RSS Feeds**: 新闻数据源
- **USGS/JORC**: 储量数据源
- **Metals-API/Commodities-API**: 价格数据源

## API 密钥获取

### OpenAI API Key (必需)
1. 访问 https://platform.openai.com/
2. 注册/登录账号
3. 在 API Keys 页面创建新密钥

### Metals-API Key (可选)
1. 访问 https://metals-api.com/
2. 注册免费账号
3. 获取 API Key

### Commodities-API Key (可选)
1. 访问 https://commodities-api.com/
2. 注册免费账号
3. 获取 API Key

## 注意事项

1. **API 费用**: OpenAI API 调用会产生费用，建议监控使用量
2. **数据时效性**: RSS 新闻实时更新，价格数据每小时更新
3. **数据准确性**: 数据来源于公开渠道，仅供参考
4. **网络连接**: 需要稳定的网络连接访问外部数据源

## 免责声明

本系统生成的报告数据来源于公开渠道，仅供参考。投资决策请咨询专业机构。系统开发者不对使用本系统产生的任何损失负责。

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
