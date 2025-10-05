"""
List available MCP tools

Debug script to see what tools are available from MCP server
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcp.mcp_client import MCPClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def main():
    print("Connecting to MCP Server...")
    client = MCPClient()

    try:
        client.connect()
        print("[OK] Connected successfully\n")

        print("Available Tools:")
        print("=" * 80)

        tools = client.list_tools()

        if not tools:
            print("No tools found!")
        else:
            for i, tool in enumerate(tools, 1):
                print(f"\n{i}. {tool.name}")
                print(f"   Description: {tool.description}")
                print(f"   Parameters:")
                for param in tool.parameters:
                    required = " (required)" if param.get('required') else " (optional)"
                    print(f"      - {param.get('name')}: {param.get('type')}{required}")
                    if param.get('description'):
                        print(f"        {param.get('description')}")

        print("\n" + "=" * 80)
        print(f"Total tools: {len(tools)}")

    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        client.disconnect()

    return 0

if __name__ == "__main__":
    sys.exit(main())
