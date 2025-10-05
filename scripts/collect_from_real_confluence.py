"""
Collect Data from Real Confluence via MCP Server

This script collects pages from the real Confluence instance running at localhost:8090
through the mcp-atlassian Docker container.

Prerequisites:
1. Confluence and MCP server containers must be running
2. MCP server should be accessible at localhost:9000
"""
import sys
import os
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.mcp.mcp_client import MCPClient
from app.mcp.confluence_collector import ConfluenceCollector
from app.utils.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mcp_connection(client: MCPClient) -> bool:
    """Test MCP server connection"""
    try:
        logger.info("Testing MCP server connection...")
        client.connect()

        tools = client.list_tools()
        logger.info(f"✓ Connected to MCP server")
        logger.info(f"✓ Available tools: {len(tools)}")

        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")

        # Check if Confluence tools are available
        confluence_tools = [t for t in tools if 'confluence' in t.name.lower()]
        if not confluence_tools:
            logger.error("✗ No Confluence tools found!")
            logger.error("  This might mean the MCP server couldn't authenticate with Confluence")
            logger.error("  Check docker logs: docker logs mcp-atlassian")
            return False

        logger.info(f"✓ Found {len(confluence_tools)} Confluence tools")
        return True

    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False


def collect_confluence_data(
    host: str = "localhost",
    port: int = 9000,
    max_pages: int = 50,
    spaces: list = None
):
    """
    Collect Confluence pages from real MCP server

    Args:
        host: MCP server host
        port: MCP server port (9000 for real server)
        max_pages: Maximum pages to collect per space
        spaces: List of space keys to collect from (None = all spaces)
    """
    logger.info("="*80)
    logger.info("Collecting Confluence Data from Real MCP Server")
    logger.info("="*80)
    logger.info(f"MCP Server: {host}:{port}")
    logger.info(f"Max pages per space: {max_pages}")
    logger.info(f"Target spaces: {spaces if spaces else 'ALL'}")
    logger.info("="*80)

    # Initialize MCP client
    client = MCPClient(host=host, port=port, timeout=30)

    # Test connection first
    if not test_mcp_connection(client):
        logger.error("\nConnection test failed. Aborting.")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check if containers are running:")
        logger.info("   docker ps | grep -E 'confluence|mcp-atlassian'")
        logger.info("2. Check MCP server logs:")
        logger.info("   docker logs mcp-atlassian")
        logger.info("3. Check Confluence accessibility:")
        logger.info("   curl http://localhost:8090")
        return

    # Initialize collector
    db_path = str(project_root / "app" / "data" / "cache" / "confluence_real.db")
    collector = ConfluenceCollector(client, db_path)

    logger.info(f"\n✓ Collector initialized with database: {db_path}")

    # Step 1: List available spaces
    logger.info("\n" + "="*80)
    logger.info("STEP 1: Listing Available Spaces")
    logger.info("="*80)

    available_spaces = collector.list_spaces()

    if not available_spaces:
        logger.warning("No spaces found!")
        logger.info("\nThis could mean:")
        logger.info("1. Confluence is empty (no spaces created yet)")
        logger.info("2. MCP server authentication issue")
        logger.info("3. Go to http://localhost:8090 and create a space first")
        return

    logger.info(f"\n✓ Found {len(available_spaces)} spaces:")
    for space in available_spaces:
        logger.info(f"  - {space.get('key', 'N/A')}: {space.get('name', 'N/A')} ({space.get('type', 'N/A')})")

    # Step 2: Collect pages
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Collecting Pages")
    logger.info("="*80)

    # Determine which spaces to collect from
    target_spaces = spaces if spaces else [s.get('key') for s in available_spaces if s.get('key')]

    if not target_spaces:
        logger.error("No target spaces specified and no spaces available!")
        return

    logger.info(f"Collecting from {len(target_spaces)} space(s): {', '.join(target_spaces)}")

    all_pages = []
    for space_key in target_spaces:
        logger.info(f"\n→ Collecting from space: {space_key}")

        try:
            pages = collector.list_pages(space_key=space_key, limit=max_pages)

            if pages:
                logger.info(f"  ✓ Found {len(pages)} pages")
                all_pages.extend(pages)

                # Show sample pages
                for i, page in enumerate(pages[:3], 1):
                    logger.info(f"    {i}. {page.title} (ID: {page.id})")

                if len(pages) > 3:
                    logger.info(f"    ... and {len(pages) - 3} more pages")
            else:
                logger.warning(f"  ✗ No pages found in {space_key}")

        except Exception as e:
            logger.error(f"  ✗ Error collecting from {space_key}: {e}")

    if not all_pages:
        logger.warning("\n⚠ No pages collected!")
        logger.info("\nPossible reasons:")
        logger.info("1. The spaces are empty - go to http://localhost:8090 and create some pages")
        logger.info("2. MCP server permissions issue")
        logger.info("3. Check MCP server logs: docker logs mcp-atlassian")
        return

    # Step 3: Save to database
    logger.info("\n" + "="*80)
    logger.info("STEP 3: Saving to Database")
    logger.info("="*80)

    try:
        saved_count = collector.save_to_cache(all_pages)
        logger.info(f"✓ Saved {saved_count} pages to database")
    except Exception as e:
        logger.error(f"✗ Failed to save pages: {e}")
        return

    # Step 4: Show statistics
    logger.info("\n" + "="*80)
    logger.info("STEP 4: Collection Statistics")
    logger.info("="*80)

    stats = collector.get_collection_stats()

    logger.info(f"\n📊 Collection Summary:")
    logger.info(f"  Total pages: {stats['total_pages']}")
    logger.info(f"  Total spaces: {stats['total_spaces']}")
    logger.info(f"  Last sync: {stats['last_sync']}")

    if stats['space_distribution']:
        logger.info(f"\n  Pages per space:")
        for space, count in stats['space_distribution'].items():
            logger.info(f"    {space}: {count} pages")

    if stats['date_range']['oldest']:
        logger.info(f"\n  Date range:")
        logger.info(f"    Oldest: {stats['date_range']['oldest']}")
        logger.info(f"    Newest: {stats['date_range']['newest']}")

    logger.info("\n" + "="*80)
    logger.info("✓ Collection completed successfully!")
    logger.info("="*80)
    logger.info(f"\nDatabase location: {db_path}")
    logger.info("You can now use this data for RAG indexing.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect Confluence pages from real MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect from all spaces (max 50 pages per space)
  python scripts/collect_from_real_confluence.py

  # Collect from specific spaces
  python scripts/collect_from_real_confluence.py --spaces MY_TEST CS TECH

  # Collect more pages
  python scripts/collect_from_real_confluence.py --max-pages 100

  # Use different MCP server port
  python scripts/collect_from_real_confluence.py --port 9001  # For mock server

Prerequisites:
  1. Start Docker containers:
     docker-compose up -d

  2. Verify containers are running:
     docker ps | grep -E 'confluence|mcp-atlassian'

  3. Access Confluence and create some content:
     http://localhost:8090
        """
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="MCP server host (default: localhost)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="MCP server port (default: 9000 for real server, 9001 for mock)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum pages to collect per space (default: 50)"
    )

    parser.add_argument(
        "--spaces",
        nargs="+",
        help="Space keys to collect from (default: all spaces)"
    )

    args = parser.parse_args()

    # Run collection
    collect_confluence_data(
        host=args.host,
        port=args.port,
        max_pages=args.max_pages,
        spaces=args.spaces
    )
