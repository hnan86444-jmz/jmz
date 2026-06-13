# -*- coding: utf-8 -*-
import sys
import io

# Windows 终端编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from mcp.server import FastMCP
import json
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import os

app = FastMCP("news-server", "1.0.0")

# 真实新闻源RSS feeds
RSS_SOURCES = {
    "mining": [
        {
            "name": "Mining.com",
            "url": "https://www.mining.com/feed/",
            "language": "en"
        },
        {
            "name": "Mining News",
            "url": "https://www.miningnews.net/rss",
            "language": "en"
        },
        {
            "name": "Australian Mining",
            "url": "https://www.australianmining.com.au/feed/",
            "language": "en"
        }
    ],
    "chinese": [
        {
            "name": "中国矿业报",
            "url": "http://www.cnmn.com.cn/rss/news.xml",
            "language": "zh"
        }
    ]
}

# 矿物关键词映射
MINERAL_KEYWORDS = {
    "lithium": ["lithium", "锂", "lithium carbonate", "spodumene", "锂矿", "锂离子"],
    "copper": ["copper", "铜", "铜矿", "copper concentrate"],
    "iron": ["iron ore", "铁矿石", "铁", "iron", "steel", "钢铁"],
    "gold": ["gold", "黄金", "金矿", "precious metal"],
    "nickel": ["nickel", "镍", "镍矿"],
    "cobalt": ["cobalt", "钴", "钴矿"],
    "aluminum": ["aluminum", "aluminium", "铝", "铝土矿", "bauxite"]
}

def fetch_rss_news(rss_url: str, source_name: str, max_items: int = 10) -> list:
    """从RSS feed获取新闻"""
    news_items = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:max_items]:
            # 清理HTML标签
            soup = BeautifulSoup(entry.get('summary', ''), 'html.parser')
            summary = soup.get_text()[:300] if soup.get_text() else ""
            
            news_items.append({
                "title": entry.get('title', ''),
                "source": source_name,
                "url": entry.get('link', ''),
                "date": entry.get('published', datetime.now().strftime("%Y-%m-%d")),
                "summary": summary,
                "fetched_at": datetime.now().isoformat()
            })
    except Exception as e:
        print(f"Error fetching from {rss_url}: {str(e)}")
    return news_items

def filter_news_by_mineral(news_items: list, mineral: str) -> list:
    """根据矿物类型筛选新闻"""
    keywords = MINERAL_KEYWORDS.get(mineral.lower(), [mineral.lower()])
    filtered = []
    
    for item in news_items:
        title_lower = item['title'].lower()
        summary_lower = item['summary'].lower()
        
        for keyword in keywords:
            if keyword.lower() in title_lower or keyword.lower() in summary_lower:
                filtered.append(item)
                break
    
    return filtered

@app.tool("get_mining_news", description="获取指定矿种的真实新闻资讯，数据来源真实可追溯")
def get_mining_news(mineral: str = "lithium", max_items: int = 5) -> str:
    """获取指定矿种的真实新闻"""
    all_news = []
    
    # 从所有RSS源获取新闻
    for category, sources in RSS_SOURCES.items():
        for source in sources:
            news = fetch_rss_news(source['url'], source['name'], max_items * 2)
            all_news.extend(news)
    
    # 按矿物类型筛选
    filtered_news = filter_news_by_mineral(all_news, mineral)
    
    # 如果筛选结果不足，返回通用矿业新闻
    if len(filtered_news) < 3:
        filtered_news = all_news[:max_items]
    else:
        filtered_news = filtered_news[:max_items]
    
    # 添加数据来源信息
    result = {
        "mineral": mineral,
        "total_found": len(filtered_news),
        "data_source": "Real-time RSS feeds from mining news websites",
        "sources_used": list(set(item['source'] for item in filtered_news)),
        "fetched_at": datetime.now().isoformat(),
        "news": filtered_news
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)

@app.tool("get_news_summary", description="对新闻数据进行摘要处理，包含来源追溯")
def get_news_summary(news_data: str) -> str:
    """生成新闻摘要，包含来源信息"""
    try:
        data = json.loads(news_data)
        news_items = data.get('news', data) if isinstance(data, dict) else data
        
        summary_lines = []
        summary_lines.append(f"=== 新闻摘要 ===")
        summary_lines.append(f"获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if isinstance(data, dict) and 'sources_used' in data:
            summary_lines.append(f"数据来源: {', '.join(data['sources_used'])}")
        summary_lines.append("")
        
        for i, item in enumerate(news_items, 1):
            summary_lines.append(f"{i}. {item['title']}")
            summary_lines.append(f"   来源: {item['source']}")
            summary_lines.append(f"   日期: {item.get('date', '未知')}")
            summary_lines.append(f"   链接: {item['url']}")
            summary_lines.append(f"   摘要: {item.get('summary', '')[:100]}...")
            summary_lines.append("")
        
        return "\n".join(summary_lines)
    except Exception as e:
        return f"解析新闻数据失败: {str(e)}"

@app.tool("get_available_sources", description="获取可用的新闻数据源列表")
def get_available_sources() -> str:
    """返回所有可用的新闻源"""
    sources_info = []
    for category, sources in RSS_SOURCES.items():
        for source in sources:
            sources_info.append({
                "name": source['name'],
                "url": source['url'],
                "language": source['language'],
                "category": category
            })
    
    return json.dumps({
        "total_sources": len(sources_info),
        "sources": sources_info
    }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app.streamable_http_app(), host="0.0.0.0", port=8001)
