"""
Mining Agent - 基于LangGraph的智能矿业日报生成器
使用真实的智能体架构，能够智能解析用户输入并调用MCP工具
"""

import os
import sys
import io
import json
import requests
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, Literal
from dotenv import load_dotenv

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages


# ============== MCP Server Client ==============
class MCPServerClient:
    """MCP Server HTTP Client - 与MCP服务器通信"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
        self.protocol_version = "2024-11-05"
    
    def _get_session(self):
        response = requests.get(self.base_url, headers={"Accept": "text/event-stream"}, stream=True, timeout=30)
        self.session_id = response.headers.get("mcp-session-id")
        return self.session_id
    
    def _send_request(self, method: str, req_id: int, params: dict = None):
        if not self.session_id:
            self._get_session()
        
        response = requests.post(
            self.base_url,
            json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": self.session_id
            },
            timeout=30
        )
        
        response.encoding = 'utf-8'
        
        for line in response.text.split('\n'):
            if line.startswith('data:'):
                data = line[5:].strip()
                if data:
                    return json.loads(data)
        return None
    
    def initialize(self):
        result = self._send_request("initialize", 1, {
            "protocolVersion": self.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "mining-agent", "version": "1.0.0"}
        })
        return result and 'result' in result
    
    def call_tool(self, tool_name: str, arguments: dict = None):
        result = self._send_request("tools/call", 3, {
            "name": tool_name,
            "arguments": arguments or {}
        })
        if result and 'result' in result:
            content = result['result'].get('content', [])
            for c in content:
                if c.get('type') == 'text':
                    return c['text']
        return None
    
    def close(self):
        if self.session_id:
            self._send_request("shutdown", 100, {})
            self.session_id = None


# ============== Configuration from Environment Variables ==============
# MCP Server URLs (可通过环境变量配置，默认使用本地地址)
NEWS_SERVER_URL = os.getenv("MCP_NEWS_SERVER_URL", "http://localhost:8001/mcp")
MINING_SERVER_URL = os.getenv("MCP_MINING_SERVER_URL", "http://localhost:8002/mcp")
PRICE_SERVER_URL = os.getenv("MCP_PRICE_SERVER_URL", "http://localhost:8003/mcp")

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def create_llm():
    """创建LLM实例，支持自定义base_url和模型"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 环境变量未设置！请在 .env 文件中配置")
    
    kwargs = {
        "model": OPENAI_MODEL,
        "temperature": 0,
        "api_key": OPENAI_API_KEY,
    }
    
    # 如果配置了自定义base_url（非默认值），则使用
    if OPENAI_BASE_URL and OPENAI_BASE_URL != "https://api.openai.com/v1":
        kwargs["base_url"] = OPENAI_BASE_URL
        print(f"[DEBUG] 使用自定义API地址: {OPENAI_BASE_URL}")
    
    print(f"[DEBUG] 使用模型: {OPENAI_MODEL}")
    
    return ChatOpenAI(**kwargs)


# ============== MCP Tools for LangChain ==============
# 全局MCP客户端
news_client = MCPServerClient(NEWS_SERVER_URL)
mining_client = MCPServerClient(MINING_SERVER_URL)
price_client = MCPServerClient(PRICE_SERVER_URL)


@tool
def get_mining_news(mineral: str = "lithium", max_items: int = 5) -> str:
    """
    获取指定矿种的新闻资讯。
    
    参数:
        mineral: 矿物类型，如 lithium, copper, iron, gold, nickel
        max_items: 返回的新闻数量
    
    返回:
        包含新闻标题、来源、日期、链接的JSON字符串
    """
    result = news_client.call_tool('get_mining_news', {'mineral': mineral, 'max_items': max_items})
    if result:
        return result
    return json.dumps({"error": "无法获取新闻数据", "news": []})


@tool
def get_reserve_data(mineral: str = "lithium", region: str = "global") -> str:
    """
    获取指定矿种和地区的储量数据。
    
    参数:
        mineral: 矿物类型，如 lithium, copper, iron
        region: 地区，如 global, pilbara, australia, chile, china
    
    返回:
        包含储量、资源量、分布情况的JSON字符串
    """
    result = mining_client.call_tool('get_reserve_data', {'mineral': mineral, 'region': region})
    if result:
        return result
    return json.dumps({"error": "无法获取储量数据"})


@tool
def get_price_data(mineral: str = "lithium") -> str:
    """
    获取指定矿种的价格数据。
    
    参数:
        mineral: 矿物类型，如 lithium, copper, iron, gold, nickel
    
    返回:
        包含当前价格、单位、数据来源的JSON字符串
    """
    result = price_client.call_tool('get_price_data', {'mineral': mineral})
    if result:
        return result
    return json.dumps({"error": "无法获取价格数据"})


@tool
def get_production_stats(mineral: str = "lithium") -> str:
    """
    获取指定矿种的产量统计数据。
    
    参数:
        mineral: 矿物类型，如 lithium, copper, iron
    
    返回:
        包含全球产量、国家分布、主要生产商的JSON字符串
    """
    result = mining_client.call_tool('get_production_stats', {'mineral': mineral})
    if result:
        return result
    return json.dumps({"error": "无法获取产量数据"})


@tool
def get_deposit_details(deposit_name: str) -> str:
    """
    获取指定矿床的详细信息。
    
    参数:
        deposit_name: 矿床名称，如 Pilgangoora, Greenbushes, Mount Marion, Wodgina
    
    返回:
        包含矿床位置、资源量、品位、运营状态的JSON字符串
    """
    result = mining_client.call_tool('get_deposit_details', {'deposit_name': deposit_name})
    if result:
        return result
    return json.dumps({"error": f"未找到矿床: {deposit_name}"})


# ============== Agent State ==============
class AgentState(TypedDict):
    """智能体状态"""
    messages: Annotated[Sequence[HumanMessage | AIMessage], add_messages]
    user_query: str
    parsed_intent: dict
    collected_data: dict
    report: str
    data_sources: list


# ============== Agent Nodes ==============
def parse_intent_node(state: AgentState) -> dict:
    """
    意图解析节点 - 使用LLM解析用户输入，确定查询意图
    """
    llm = create_llm()
    
    system_prompt = """你是一个矿业数据分析助手。请分析用户的查询，提取以下信息：
    
1. 矿物类型 (mineral): lithium, copper, iron, gold, nickel 等
2. 地区 (region): global, pilbara, australia, chile, china 等
3. 查询类型 (query_type): 
   - "news" - 新闻查询
   - "reserves" - 储量查询
   - "price" - 价格查询
   - "production" - 产量查询
   - "deposit" - 矿床查询
   - "comprehensive" - 综合报告（包含以上所有）
4. 具体矿床名称 (deposit_name): 如果用户提到了具体矿床

请以JSON格式返回结果，例如：
{"mineral": "lithium", "region": "pilbara", "query_type": "comprehensive", "deposit_name": null}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请分析以下查询：{state['user_query']}")
    ]
    
    response = llm.invoke(messages)
    
    # 解析LLM返回的JSON
    try:
        # 提取JSON部分
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        parsed = json.loads(content.strip())
    except:
        # 默认值
        parsed = {
            "mineral": "lithium",
            "region": "global",
            "query_type": "comprehensive",
            "deposit_name": None
        }
    
    return {
        "parsed_intent": parsed,
        "messages": [AIMessage(content=f"已解析查询意图: {json.dumps(parsed, ensure_ascii=False)}")]
    }


def should_collect_news(state: AgentState) -> bool:
    """判断是否需要收集新闻数据"""
    query_type = state["parsed_intent"].get("query_type", "comprehensive")
    return query_type in ["news", "comprehensive"]


def should_collect_reserves(state: AgentState) -> bool:
    """判断是否需要收集储量数据"""
    query_type = state["parsed_intent"].get("query_type", "comprehensive")
    return query_type in ["reserves", "comprehensive"]


def should_collect_price(state: AgentState) -> bool:
    """判断是否需要收集价格数据"""
    query_type = state["parsed_intent"].get("query_type", "comprehensive")
    return query_type in ["price", "comprehensive"]


def should_collect_production(state: AgentState) -> bool:
    """判断是否需要收集产量数据"""
    query_type = state["parsed_intent"].get("query_type", "comprehensive")
    return query_type in ["production", "comprehensive"]


def collect_news_node(state: AgentState) -> dict:
    """收集新闻数据节点"""
    mineral = state["parsed_intent"].get("mineral", "lithium")
    
    news_data = get_mining_news.invoke({"mineral": mineral, "max_items": 5})
    
    collected_data = state.get("collected_data", {})
    collected_data["news"] = json.loads(news_data) if isinstance(news_data, str) else news_data
    
    data_sources = state.get("data_sources", [])
    if isinstance(collected_data["news"], dict) and "sources_used" in collected_data["news"]:
        # 获取新闻来源详情
        news_sources = []
        if "news" in collected_data["news"]:
            for news_item in collected_data["news"]["news"]:
                source_info = f"{news_item.get('source', '')}"
                if news_item.get('url'):
                    source_info += f" ({news_item.get('url')})"
                news_sources.append(source_info)
        
        data_sources.append({
            "type": "news",
            "sources": news_sources if news_sources else collected_data["news"].get("sources_used", []),
            "fetched_at": collected_data["news"].get("fetched_at", "")
        })
    
    return {
        "collected_data": collected_data,
        "data_sources": data_sources,
        "messages": [AIMessage(content=f"已收集{mineral}相关新闻数据")]
    }


def collect_reserves_node(state: AgentState) -> dict:
    """收集储量数据节点"""
    mineral = state["parsed_intent"].get("mineral", "lithium")
    region = state["parsed_intent"].get("region", "global")
    
    reserve_data = get_reserve_data.invoke({"mineral": mineral, "region": region})
    
    collected_data = state.get("collected_data", {})
    collected_data["reserves"] = json.loads(reserve_data) if isinstance(reserve_data, str) else reserve_data
    
    data_sources = state.get("data_sources", [])
    if isinstance(collected_data["reserves"], dict) and "data_source" in collected_data["reserves"]:
        data_sources.append({
            "type": "reserves",
            "source": collected_data["reserves"].get("data_source", ""),
            "source_url": collected_data["reserves"].get("source_url", ""),
            "fetched_at": collected_data["reserves"].get("query_time", "")
        })
    
    return {
        "collected_data": collected_data,
        "data_sources": data_sources,
        "messages": [AIMessage(content=f"已收集{region}地区{mineral}储量数据")]
    }


def collect_price_node(state: AgentState) -> dict:
    """收集价格数据节点"""
    mineral = state["parsed_intent"].get("mineral", "lithium")
    
    price_data = get_price_data.invoke({"mineral": mineral})
    
    collected_data = state.get("collected_data", {})
    collected_data["price"] = json.loads(price_data) if isinstance(price_data, str) else price_data
    
    data_sources = state.get("data_sources", [])
    if isinstance(collected_data["price"], dict) and "data_source" in collected_data["price"]:
        data_sources.append({
            "type": "price",
            "source": collected_data["price"].get("data_source", ""),
            "source_url": collected_data["price"].get("source_url", ""),
            "fetched_at": collected_data["price"].get("update_time", "")
        })
    
    return {
        "collected_data": collected_data,
        "data_sources": data_sources,
        "messages": [AIMessage(content=f"已收集{mineral}价格数据")]
    }


def collect_production_node(state: AgentState) -> dict:
    """收集产量数据节点"""
    mineral = state["parsed_intent"].get("mineral", "lithium")
    
    production_data = get_production_stats.invoke({"mineral": mineral})
    
    collected_data = state.get("collected_data", {})
    collected_data["production"] = json.loads(production_data) if isinstance(production_data, str) else production_data
    
    return {
        "collected_data": collected_data,
        "messages": [AIMessage(content=f"已收集{mineral}产量数据")]
    }


def generate_report_node(state: AgentState) -> dict:
    """
    生成报告节点 - 使用LLM整理数据并生成结构化报告
    """
    llm = create_llm()
    
    mineral = state["parsed_intent"].get("mineral", "lithium")
    region = state["parsed_intent"].get("region", "global")
    collected_data = state.get("collected_data", {})
    data_sources = state.get("data_sources", [])
    
    # 矿物中文名称
    mineral_names = {
        "lithium": "锂",
        "copper": "铜",
        "iron": "铁",
        "gold": "金",
        "nickel": "镍"
    }
    mineral_cn = mineral_names.get(mineral.lower(), mineral)
    
    # 构建报告生成提示
    system_prompt = f"""你是一个专业的矿业分析师。请根据以下数据生成一份结构化的矿业日报。

矿物类型: {mineral_cn}矿 ({mineral})
地区: {region}

数据如下（JSON格式）:
{json.dumps(collected_data, ensure_ascii=False, indent=2)}

请生成一份包含以下内容的Markdown格式报告：
1. 标题和生成时间
2. 新闻摘要（如有）
3. 储量数据（如有）
4. 价格数据（如有）
5. 产量数据（如有）
6. 风险分析
7. 数据来源追溯

要求：
- 使用中文
- 数据准确，引用来源
- 分析专业、客观
- 格式清晰、易读
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="请生成矿业日报")
    ]
    
    response = llm.invoke(messages)
    report = response.content
    
    # 添加数据来源追溯部分
    if data_sources:
        report += "\n\n---\n\n## 📋 数据来源追溯\n\n"
        report += "本报告数据来源于以下渠道：\n\n"
        for i, source in enumerate(data_sources, 1):
            report += f"### {i}. {source.get('type', '').title()} 数据\n"
            if isinstance(source.get('sources'), list):
                for s in source.get('sources', []):
                    report += f"- {s}\n"
            else:
                report += f"- **来源**: {source.get('source', '未知')}\n"
                if source.get('source_url'):
                    report += f"- **链接**: {source.get('source_url')}\n"
            report += f"- **获取时间**: {source.get('fetched_at', '未知')}\n\n"
    
    report += f"\n---\n\n**报告生成时间**: {datetime.now().isoformat()}\n"
    report += "\n*免责声明：本报告数据来源于公开渠道，仅供参考。投资决策请咨询专业机构。*"
    
    return {
        "report": report,
        "messages": [AIMessage(content="报告生成完成")]
    }


def save_report_node(state: AgentState) -> dict:
    """保存报告节点"""
    report = state.get("report", "")
    
    if report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mining_report_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        return {
            "messages": [AIMessage(content=f"报告已保存到: {filename}")]
        }
    
    return {"messages": [AIMessage(content="报告生成失败")]}


# ============== Build Agent Graph ==============
def build_mining_agent():
    """构建矿业智能体工作流图"""
    
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("collect_news", collect_news_node)
    workflow.add_node("collect_reserves", collect_reserves_node)
    workflow.add_node("collect_price", collect_price_node)
    workflow.add_node("collect_production", collect_production_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("save_report", save_report_node)
    
    # 设置入口
    workflow.set_entry_point("parse_intent")
    
    # 添加条件边 - 根据查询类型决定收集哪些数据
    workflow.add_conditional_edges(
        "parse_intent",
        lambda state: state["parsed_intent"].get("query_type", "comprehensive"),
        {
            "news": "collect_news",
            "reserves": "collect_reserves",
            "price": "collect_price",
            "production": "collect_production",
            "deposit": "collect_reserves",
            "comprehensive": "collect_news"
        }
    )
    
    # 综合报告的数据收集流程
    workflow.add_edge("collect_news", "collect_reserves")
    workflow.add_edge("collect_reserves", "collect_price")
    workflow.add_edge("collect_price", "collect_production")
    workflow.add_edge("collect_production", "generate_report")
    
    # 单一类型查询直接生成报告
    workflow.add_edge("collect_news", "generate_report")
    workflow.add_edge("collect_reserves", "generate_report")
    workflow.add_edge("collect_price", "generate_report")
    workflow.add_edge("collect_production", "generate_report")
    
    # 保存报告
    workflow.add_edge("generate_report", "save_report")
    workflow.add_edge("save_report", END)
    
    return workflow.compile()


# ============== Main Function ==============
def main():
    print("=" * 60)
    print("    MCP Mining Agent - Intelligent Report Generator")
    print("=" * 60)
    print("\n欢迎使用智能矿业日报生成器！")
    print("我可以理解您的查询并自动获取相关数据。")
    print("\n支持查询类型：")
    print("  - 新闻查询: '锂矿最新新闻'")
    print("  - 储量查询: 'Pilbara地区锂矿储量'")
    print("  - 价格查询: '铜矿价格'")
    print("  - 产量查询: '全球锂矿产量'")
    print("  - 综合报告: '生成Pilbara锂矿日报'")
    print("\n支持矿物: lithium(锂), copper(铜), iron(铁), gold(金), nickel(镍)")
    print("支持地区: global, pilbara, australia, chile, china")
    print("")
    
    # 初始化MCP客户端
    print("[1] 初始化 MCP 服务器连接...")
    try:
        news_client.initialize()
        mining_client.initialize()
        price_client.initialize()
        print("[OK] MCP 服务器连接成功！")
    except Exception as e:
        print(f"[ERROR] MCP 服务器连接失败: {e}")
        print("请确保MCP服务器正在运行:")
        print("  python servers/news_server.py")
        print("  python servers/mining_data_server.py")
        print("  python servers/price_server.py")
        return
    
    # 检查OpenAI API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[WARNING] 未设置 OPENAI_API_KEY 环境变量")
        print("请设置环境变量或在 .env 文件中配置")
        print("示例: OPENAI_API_KEY=sk-xxx")
        return
    
    # 显示当前配置
    print(f"\n[2] 当前配置:")
    print(f"    LLM 模型: {OPENAI_MODEL}")
    print(f"    API Base: {OPENAI_BASE_URL}")
    print(f"    新闻服务器: {NEWS_SERVER_URL}")
    print(f"    储量服务器: {MINING_SERVER_URL}")
    print(f"    价格服务器: {PRICE_SERVER_URL}")
    
    # 获取用户输入
    query = input("\n[3] 请输入您的查询: ")
    if not query.strip():
        query = "生成Pilbara地区锂矿综合日报"
        print(f"    使用默认查询: {query}")
    
    print("\n[4] 智能体正在分析查询并收集数据...")
    
    # 构建并运行智能体
    try:
        agent = build_mining_agent()
        
        # 初始化状态
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "parsed_intent": {},
            "collected_data": {},
            "report": "",
            "data_sources": []
        }
        
        # 运行智能体
        result = agent.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print("智能体执行完成")
        print("=" * 60)
        
        # 打印消息
        for msg in result.get("messages", []):
            if hasattr(msg, 'content'):
                print(f"  {msg.content}")
        
        # 显示报告
        if result.get("report"):
            print("\n" + "=" * 60)
            print("生成的报告")
            print("=" * 60)
            print(result["report"][:2000])  # 显示前2000字符
            if len(result["report"]) > 2000:
                print("\n... (报告已截断，完整内容请查看生成的文件)")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 智能矿业日报生成完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 智能体执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭MCP客户端
        news_client.close()
        mining_client.close()
        price_client.close()


if __name__ == "__main__":
    main()
