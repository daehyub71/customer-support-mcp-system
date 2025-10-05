"""
Test Data Collectors with Mock MCP Server

This script tests the Jira and Confluence collectors using the mock MCP server.
Run the mock server first: python scripts/mock_mcp_server.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mcp.mcp_client import MCPClient
from app.mcp.jira_collector import JiraCollector
from app.mcp.confluence_collector import ConfluenceCollector


def test_jira_collection():
    """Test Jira data collection"""
    print("=" * 80)
    print("Testing Jira Collection with Mock Server")
    print("=" * 80)

    # Connect to mock MCP server
    client = MCPClient(host="localhost", port=9001, timeout=30)

    try:
        # Connect
        print("\n1. Connecting to mock MCP server...")
        client.connect()
        print("   [OK] Connected")

        # List tools
        print("\n2. Listing available tools...")
        tools = client.list_tools()
        print(f"   [OK] Found {len(tools)} tools")
        for tool in tools:
            print(f"        - {tool.name}: {tool.description}")

        # Create collector
        print("\n3. Creating Jira collector...")
        collector = JiraCollector(client, db_path="app/data/cache/test_jira_cache.db")
        print("   [OK] Collector created")

        # Collect issues
        print("\n4. Collecting Jira issues...")
        issues = collector.collect_issues(
            jql="status IN (Done, Resolved) ORDER BY updated DESC",
            max_results=20
        )
        print(f"   [OK] Collected {len(issues)} issues")
        print(f"   [OK] Saved to database")

        # Show sample
        if issues:
            print("\n5. Sample issue:")
            issue = issues[0]
            print(f"   Key: {issue.key}")
            print(f"   Summary: {issue.summary}")
            print(f"   Status: {issue.status}")

        print("\n[SUCCESS] Jira collection test completed")

    finally:
        client.disconnect()


def test_confluence_collection():
    """Test Confluence data collection"""
    print("\n" + "=" * 80)
    print("Testing Confluence Collection with Mock Server")
    print("=" * 80)

    # Connect to mock MCP server
    client = MCPClient(host="localhost", port=9001, timeout=30)

    try:
        # Connect
        print("\n1. Connecting to mock MCP server...")
        client.connect()
        print("   [OK] Connected")

        # Create collector
        print("\n2. Creating Confluence collector...")
        collector = ConfluenceCollector(client, db_path="app/data/cache/test_confluence_cache.db")
        print("   [OK] Collector created")

        # Collect pages
        print("\n3. Collecting Confluence pages...")
        pages = collector.list_pages(space_key="MOCK", limit=15)
        print(f"   [OK] Found {len(pages)} pages")

        # Save to cache
        if pages:
            print("\n4. Saving to database...")
            saved = collector.save_to_cache(pages)
            print(f"   [OK] Saved {saved} pages")

        # Show sample
        if pages:
            print("\n5. Sample page:")
            page = pages[0]
            print(f"   ID: {page.id}")
            print(f"   Title: {page.title}")
            print(f"   Space: {page.space}")

        print("\n[SUCCESS] Confluence collection test completed")

    finally:
        client.disconnect()


if __name__ == "__main__":
    print("\nMake sure the mock MCP server is running:")
    print("  python scripts/mock_mcp_server.py")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)

    # Run tests
    test_jira_collection()
    test_confluence_collection()

    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
