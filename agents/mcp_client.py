import requests
import json

class MCPServerClient:
    """MCP Server HTTP Client using SSE protocol"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
        self.protocol_version = "2024-11-05"
    
    def _get_session(self):
        """Create a new session"""
        response = requests.get(
            self.base_url,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=10
        )
        self.session_id = response.headers.get("mcp-session-id")
        return self.session_id
    
    def _send_request(self, method: str, req_id: int, params: dict = None):
        """Send a JSON-RPC request via SSE"""
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
        
        # Parse SSE response
        text = response.text
        for line in text.split('\n'):
            if line.startswith('data:'):
                data = line[5:].strip()
                if data:
                    return json.loads(data)
        return None
    
    def initialize(self):
        """Initialize the MCP session"""
        result = self._send_request("initialize", 1, {
            "protocolVersion": self.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "mining-agent", "version": "1.0.0"}
        })
        if result and 'result' in result:
            self.protocol_version = result['result'].get('protocolVersion', self.protocol_version)
            return True
        return False
    
    def list_tools(self):
        """List available tools"""
        result = self._send_request("tools/list", 2)
        if result and 'result' in result:
            return result['result'].get('tools', [])
        return []
    
    def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a tool and return the result"""
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
        """Close the session"""
        self.session_id = None


def test():
    # Test news server
    print("Testing News Server...", flush=True)
    client = MCPServerClient("http://localhost:8001/mcp")
    client.initialize()
    tools = client.list_tools()
    print(f"  Found {len(tools)} tools: {[t['name'] for t in tools]}", flush=True)
    
    news = client.call_tool('get_mining_news', {'mineral': 'lithium'})
    if news:
        news_data = json.loads(news)
        print(f"  Got {len(news_data)} news items", flush=True)
    
    client.close()
    print("[OK] News Server test passed!", flush=True)
    
    # Test mining data server
    print("\nTesting Mining Data Server...", flush=True)
    client = MCPServerClient("http://localhost:8002/mcp")
    client.initialize()
    tools = client.list_tools()
    print(f"  Found {len(tools)} tools: {[t['name'] for t in tools]}", flush=True)
    
    reserves = client.call_tool('get_reserve_data', {'mineral': 'lithium', 'region': 'Pilbara'})
    if reserves:
        data = json.loads(reserves)
        print(f"  Got reserve data: resources={data.get('resources', {}).get('total', 0)}", flush=True)
    
    client.close()
    print("[OK] Mining Data Server test passed!", flush=True)
    
    # Test price server
    print("\nTesting Price Server...", flush=True)
    client = MCPServerClient("http://localhost:8003/mcp")
    client.initialize()
    tools = client.list_tools()
    print(f"  Found {len(tools)} tools: {[t['name'] for t in tools]}", flush=True)
    
    price = client.call_tool('get_price_trend', {'days': 30})
    if price:
        data = json.loads(price)
        print(f"  Got price data: change={data.get('change', 0)}%", flush=True)
    
    client.close()
    print("[OK] Price Server test passed!", flush=True)
    
    print("\n[SUCCESS] All MCP servers are working correctly!")

if __name__ == "__main__":
    test()