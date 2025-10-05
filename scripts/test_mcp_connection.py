"""
Test MCP Connection and List Available Resources

Comprehensive test to see what the MCP server actually provides
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcp.mcp_client import MCPClient

def main():
    print("=" * 80)
    print("MCP Server Connection Test")
    print("=" * 80)

    client = MCPClient()

    try:
        # Connect
        print("\n1. Connecting to MCP Server...")
        client.connect()
        print("   [OK] Connected")
        print(f"   Session ID: {client.session_id}")

        # Server capabilities
        print("\n2. Server Capabilities:")
        if client.server_capabilities:
            print(json.dumps(client.server_capabilities, indent=2))

        # List tools
        print("\n3. Available Tools:")
        tools = client.list_tools()
        if tools:
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")
        else:
            print("   [WARN] No tools available!")

        # List resources
        print("\n4. Available Resources:")
        try:
            resources = client.list_resources()
            if resources:
                for res in resources:
                    print(f"   - {res.name} ({res.uri})")
            else:
                print("   [INFO] No resources available")
        except Exception as e:
            print(f"   [ERROR] Failed to list resources: {e}")

        # Try to call a tool (if any)
        if tools:
            print(f"\n5. Testing tool call: {tools[0].name}")
            try:
                # Try calling the first tool with minimal params
                result = client.call_tool(tools[0].name, {})
                print(f"   Result: {result}")
            except Exception as e:
                print(f"   [ERROR] {e}")

        print("\n" + "=" * 80)
        print("Connection test completed")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.disconnect()

    return 0

if __name__ == "__main__":
    sys.exit(main())
