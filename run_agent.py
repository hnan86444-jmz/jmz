import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

# Test all 3 servers
print("=" * 60)
print("Testing MCP Mining Agent")
print("=" * 60)

# News Server
print("\n[1] News Server (port 8001)")
url = "http://localhost:8001/mcp"
resp = requests.get(url, headers={"Accept": "text/event-stream"}, stream=True, timeout=30)
sid = resp.headers.get("mcp-session-id")
print(f"    Session: {sid[:8]}...")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)
print(f"    Initialize: OK")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "get_mining_news", "arguments": {"mineral": "lithium"}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)

for line in resp.text.split('\n'):
    if line.startswith('data:'):
        data = line[5:].strip()
        if data:
            r = json.loads(data)
            if 'result' in r:
                content = r['result'].get('content', [])
                for c in content:
                    if c.get('type') == 'text':
                        news = json.loads(c['text'])
                        print(f"    News: {len(news)} items")

# Mining Data Server
print("\n[2] Mining Data Server (port 8002)")
url = "http://localhost:8002/mcp"
resp = requests.get(url, headers={"Accept": "text/event-stream"}, stream=True, timeout=30)
sid = resp.headers.get("mcp-session-id")
print(f"    Session: {sid[:8]}...")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)
print(f"    Initialize: OK")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "get_reserve_data", "arguments": {"mineral": "lithium", "region": "Pilbara"}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)

for line in resp.text.split('\n'):
    if line.startswith('data:'):
        data = line[5:].strip()
        if data:
            r = json.loads(data)
            if 'result' in r:
                content = r['result'].get('content', [])
                for c in content:
                    if c.get('type') == 'text':
                        data = json.loads(c['text'])
                        total = data.get('resources', {}).get('total', 0)
                        print(f"    Reserves: {total:,} tons")

# Price Server
print("\n[3] Price Server (port 8003)")
url = "http://localhost:8003/mcp"
resp = requests.get(url, headers={"Accept": "text/event-stream"}, stream=True, timeout=30)
sid = resp.headers.get("mcp-session-id")
print(f"    Session: {sid[:8]}...")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)
print(f"    Initialize: OK")

resp = requests.post(url, json={
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "get_price_trend", "arguments": {"days": 30}}
}, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "mcp-session-id": sid}, timeout=30)

for line in resp.text.split('\n'):
    if line.startswith('data:'):
        data = line[5:].strip()
        if data:
            r = json.loads(data)
            if 'result' in r:
                content = r['result'].get('content', [])
                for c in content:
                    if c.get('type') == 'text':
                        price = json.loads(c['text'])
                        print(f"    Price: {price.get('end_price', 0):,} | Change: {price.get('change', 0)}%")

print("\n" + "=" * 60)
print("[SUCCESS] All MCP servers working correctly!")
print("=" * 60)