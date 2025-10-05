"""
Full Pipeline Demo with Mock MCP Server

Demonstrates complete data collection workflow:
1. Connect to Mock MCP Server
2. Collect Jira issues
3. Collect Confluence pages
4. Save to SQLite cache
5. Display statistics
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mcp.mcp_client import MCPClient
from app.mcp.jira_collector import JiraCollector
from app.mcp.confluence_collector import ConfluenceCollector
import time

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def demo_jira_collection():
    """Demo Jira data collection"""
    print_header("JIRA DATA COLLECTION DEMO")

    # Connect to mock MCP server
    print("\n1. Connecting to Mock MCP Server (port 9001)...")
    client = MCPClient(host="localhost", port=9001, timeout=30)
    client.connect()
    print("   [OK] Connected")

    # List tools
    print("\n2. Listing available tools...")
    tools = client.list_tools()
    jira_tools = [t for t in tools if 'jira' in t.name]
    print(f"   [OK] Found {len(jira_tools)} Jira tools:")
    for tool in jira_tools:
        print(f"        - {tool.name}")

    # Create collector
    print("\n3. Creating Jira collector with SQLite cache...")
    collector = JiraCollector(client, db_path="app/data/cache/demo_jira.db")
    print("   [OK] Collector initialized")

    # Collect issues
    print("\n4. Collecting Jira issues...")
    start = time.time()
    issues = collector.collect_issues(
        jql="status IN (Done, Resolved) ORDER BY updated DESC",
        max_results=20
    )
    elapsed = time.time() - start
    print(f"   [OK] Collected {len(issues)} issues in {elapsed:.2f}s")
    print(f"   [OK] Saved to SQLite database")

    # Show samples
    if issues:
        print("\n5. Sample Issues:")
        for i, issue in enumerate(issues[:3], 1):
            print(f"\n   Issue {i}:")
            print(f"   - Key:      {issue.key}")
            print(f"   - Summary:  {issue.summary}")
            print(f"   - Status:   {issue.status}")
            print(f"   - Assignee: {issue.assignee or 'Unassigned'}")

    # Statistics
    print("\n6. Statistics:")
    print(f"   - Total issues:     {len(issues)}")
    print(f"   - Status breakdown:")
    statuses = {}
    for issue in issues:
        statuses[issue.status] = statuses.get(issue.status, 0) + 1
    for status, count in statuses.items():
        print(f"     * {status}: {count}")

    client.disconnect()
    print("\n[SUCCESS] Jira collection completed")
    return len(issues)

def demo_confluence_collection():
    """Demo Confluence data collection"""
    print_header("CONFLUENCE DATA COLLECTION DEMO")

    # Connect
    print("\n1. Connecting to Mock MCP Server (port 9001)...")
    client = MCPClient(host="localhost", port=9001, timeout=30)
    client.connect()
    print("   [OK] Connected")

    # List tools
    print("\n2. Listing available tools...")
    tools = client.list_tools()
    conf_tools = [t for t in tools if 'confluence' in t.name]
    print(f"   [OK] Found {len(conf_tools)} Confluence tools:")
    for tool in conf_tools:
        print(f"        - {tool.name}")

    # Create collector
    print("\n3. Creating Confluence collector with SQLite cache...")
    collector = ConfluenceCollector(client, db_path="app/data/cache/demo_confluence.db")
    print("   [OK] Collector initialized")

    # Collect pages
    print("\n4. Collecting Confluence pages...")
    start = time.time()
    pages = collector.list_pages(space_key="MOCK", limit=15)
    elapsed = time.time() - start
    print(f"   [OK] Found {len(pages)} pages in {elapsed:.2f}s")

    # Save to cache
    if pages:
        print("\n5. Saving to SQLite database...")
        start = time.time()
        saved = collector.save_to_cache(pages)
        elapsed = time.time() - start
        print(f"   [OK] Saved {saved} pages in {elapsed:.2f}s")

    # Show samples
    if pages:
        print("\n6. Sample Pages:")
        for i, page in enumerate(pages[:3], 1):
            print(f"\n   Page {i}:")
            print(f"   - ID:      {page.id}")
            print(f"   - Title:   {page.title}")
            print(f"   - Space:   {page.space}")
            content_preview = page.content[:100] if page.content else "No content"
            print(f"   - Content: {content_preview}...")

    # Statistics
    print("\n7. Statistics:")
    print(f"   - Total pages:  {len(pages)}")
    print(f"   - Space: MOCK")

    client.disconnect()
    print("\n[SUCCESS] Confluence collection completed")
    return len(pages)

def main():
    """Run full pipeline demo"""
    print("\n" + "=" * 80)
    print("=  CUSTOMER SUPPORT MCP SYSTEM - FULL PIPELINE DEMO".ljust(79) + "=")
    print("=" * 80)

    print("\nThis demo shows the complete data collection pipeline using Mock MCP Server")
    print("Make sure mock server is running: python scripts/mock_mcp_server.py")

    print("\nPress Enter to start demo (or Ctrl+C to cancel)...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nDemo cancelled")
        return

    # Run demos
    jira_count = demo_jira_collection()
    confluence_count = demo_confluence_collection()

    # Summary
    print_header("DEMO SUMMARY")
    print(f"\n[OK] Jira Issues Collected:     {jira_count}")
    print(f"[OK] Confluence Pages Collected: {confluence_count}")
    print(f"[OK] Data saved to SQLite cache")
    print(f"\nDatabase files:")
    print(f"  - app/data/cache/demo_jira.db")
    print(f"  - app/data/cache/demo_confluence.db")

    print_header("NEXT STEPS")
    print("""
    1. [DONE] MCP Client Module - COMPLETE
    2. [DONE] Jira Data Collector - COMPLETE
    3. [DONE] Confluence Data Collector - COMPLETE
    4. [DONE] Mock MCP Server - COMPLETE

    5. [NEXT] Proceed to Task 2.1: RAG System Implementation
       - Vector indexing with FAISS
       - Embedding generation
       - Similarity search
       - LangGraph integration
    """)

    print("=" * 80)
    print("\n[DEMO COMPLETE] All systems operational!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
