# 智能矿业日报系统

基于 LangGraph 和 MCP (Model Context Protocol) 的智能矿业日报生成系统。

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

```bash
# Windows CMD
start.bat

# 或使用 PowerShell（更好的中文支持）
start.ps1
```

### 方式二：Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 运行 Agent
docker exec -it mining-agent python agents/mining_agent.py
```

### 方式三：手动启动

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

## 📁 项目结构

```
凌云智矿/
├── agents/
│   └── mining_agent.py          # 智能体主程序（基于 LangGraph）
├── servers/
│   ├── news_server.py           # 新闻 MCP 服务器 (端口 8001)
│   ├── mining_data_server.py    # 储量数据 MCP 服务器 (端口 8002)
│   └── price_server.py          # 价格 MCP 服务器 (端口 8003)
├── .env.example                  # 环境变量配置示例
├── .env                          # 实际环境变量文件（需创建）
├── requirements.txt              # Python 依赖
├── docker-compose.yml            # Docker 编排配置
├── start.bat                     # 快速启动脚本
├── RUN.md                        # 本文件
└── README.md                     # 详细使用说明
```

## 🔧 环境变量配置

复制 `.env.example` 为 `.env` 并配置：

```bash
# LLM 配置（必需）
OPENAI_API_KEY=sk-your-api-key-here

# LLM API 地址（可选，默认使用 OpenAI 官方）
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# MCP 服务器地址（可选，默认本地）
MCP_NEWS_SERVER_URL=http://localhost:8001/mcp
MCP_MINING_SERVER_URL=http://localhost:8002/mcp
MCP_PRICE_SERVER_URL=http://localhost:8003/mcp

# 价格 API（可选）
METALS_API_KEY=your-metals-api-key
COMMODITIES_API_KEY=your-commodities-api-key
```

### 支持的模型

- OpenAI: `gpt-3.5-turbo`, `gpt-4`, `gpt-4o`
- 第三方兼容: `deepseek-chat`, `qwen-turbo` 等

## 📋 核心功能

### 1. 智能体架构

使用 LangGraph 构建智能体工作流：

```
用户输入 → 意图解析 → 工具选择 → 数据收集 → 报告生成 → 文件保存
```

**关键组件**：
- **意图解析**: 使用 LLM 理解用户自然语言查询
- **工具选择**: 根据意图自动选择合适的 MCP 工具
- **数据收集**: 自动调用 MCP 服务器获取数据
- **报告生成**: 整理数据生成结构化报告

### 2. 真实数据源

| 数据类型 | 来源 | 说明 |
|---------|------|------|
| 新闻 | Mining.com, Mining News, Australian Mining RSS | 实时矿业新闻 |
| 储量 | USGS Mineral Commodity Summaries 2024 | 权威储量数据 |
| 价格 | Metals-API, LME, S&P Global Platts | 市场实时价格 |
| 产量 | JORC 标准报告, 公司公告 | 产量统计数据 |

### 3. 数据来源追溯

每条数据都记录：
- 数据来源名称
- 来源链接（URL）
- 获取时间

## 🎯 使用示例

### 查询类型

```
# 新闻查询
"锂矿最新新闻"
"copper mining news"

# 储量查询
"Pilbara地区锂矿储量"
"global lithium reserves"

# 价格查询
"铜矿价格"
"iron ore price today"

# 综合报告
"生成Pilbara锂矿日报"
"comprehensive lithium report"
```

### 支持的矿物

- Lithium (锂)
- Copper (铜)
- Iron (铁)
- Gold (金)
- Nickel (镍)

### 支持的地区

- Global (全球)
- Pilbara (皮尔巴拉)
- Australia (澳大利亚)
- Chile (智利)
- China (中国)

## 🔧 服务端口

| 服务 | 端口 | MCP URL |
|------|------|---------|
| News Server | 8001 | http://localhost:8001/mcp |
| Mining Data Server | 8002 | http://localhost:8002/mcp |
| Price Server | 8003 | http://localhost:8003/mcp |

## 📝 API 调用示例

### 获取新闻数据

```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_mining_news","arguments":{"mineral":"lithium","max_items":5}}}'
```

### 获取储量数据

```bash
curl -X POST http://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_reserve_data","arguments":{"mineral":"lithium","region":"pilbara"}}}'
```

### 获取价格数据

```bash
curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_price_data","arguments":{"mineral":"lithium"}}}'
```

## 📊 健康检查

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## ✅ 验证方法

### 1. 检查 MCP 服务器连接

```python
from agents.mining_agent import news_client, mining_client, price_client

news_client.initialize()
mining_client.initialize()
price_client.initialize()

print("MCP 服务器连接成功！")
```

### 2. 测试数据获取

```bash
# 运行测试脚本
python test_agent.py
```

## 📝 输出示例

```markdown
# Pilbara 地区锂矿日报

**生成时间**: 2024-01-15 10:30:00

## 📰 新闻摘要

### Pilbara Minerals 宣布扩产计划
- **来源**: Mining.com
- **日期**: 2024-01-15
- **摘要**: Pilbara Minerals 计划将 Pilgangoora 项目产能提升至 100 万吨/年...

## 📊 储量数据

### 全球锂储量
- **总储量**: 26,000,000 吨 LCE
- **数据来源**: USGS Mineral Commodity Summaries 2024

## 💰 价格数据

- **当前价格**: $13,500 USD/吨
- **数据来源**: S&P Global Platts

## 📋 数据来源追溯

### 1. News 数据
- Mining.com
- Mining News
- **获取时间**: 2024-01-15T10:30:00

### 2. Reserves 数据
- **来源**: USGS Mineral Commodity Summaries 2024
- **链接**: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-lithium.pdf
```

## 🛠️ 开发指南

### 添加新的 MCP 工具

1. 在对应的 Server 文件中添加工具定义

```python
@app.tool("get_new_data", description="获取新数据")
def get_new_data(param: str) -> str:
    # 处理逻辑
    return json.dumps(result)
```

2. 在 `mining_agent.py` 中添加对应的 LangChain Tool

```python
@tool
def get_new_data_tool(param: str) -> str:
    result = mining_client.call_tool('get_new_data', {'param': param})
    return result
```

3. 在工作流中添加新的节点

### 修改智能体工作流

编辑 `agents/mining_agent.py` 中的节点和边定义：

```python
workflow.add_node("new_node", new_node_function)
workflow.add_edge("existing_node", "new_node")
```

## 📌 注意事项

1. **API 密钥**: 必须配置 `OPENAI_API_KEY`
2. **依赖安装**: 运行前执行 `pip install -r requirements.txt`
3. **服务启动**: Agent 运行前确保 MCP 服务器已启动
4. **数据时效**: 新闻实时更新，价格数据每小时更新
5. **编码问题**: 确保使用 UTF-8 编码

## 🔗 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [MCP 协议](https://modelcontextprotocol.io/)
- [USGS 矿产数据](https://www.usgs.gov/centers/national-minerals-information-center)

## 📄 许可证

MIT License
