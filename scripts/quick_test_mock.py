"""
Quick test of mock MCP server
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mcp.mcp_client import MCPClient

# Connect to mock server on port 9001
client = MCPClient(host="localhost", port=9001, timeout=30)

print("Connecting to mock MCP server...")
client.connect()
print("[OK] Connected")

print("\nListing tools...")
tools = client.list_tools()
print(f"[OK] Found {len(tools)} tools:")
for tool in tools:
    print(f"  - {tool.name}: {tool.description}")

print("\nCalling jira_search...")
response = client.call_tool("jira_search", {"max_results": 5})
if response.isError:
    print(f"[ERROR] {response.content[0]['text']}")
else:
    import json
    data = json.loads(response.content[0]['text'])
    print(f"[OK] Found {data['total']} issues")
    if data['issues']:
        print(f"  Sample: {data['issues'][0]['key']} - {data['issues'][0]['fields']['summary']}")

print("\n[SUCCESS] Mock server test completed!")
client.disconnect()
