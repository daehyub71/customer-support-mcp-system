"""
Collect Confluence Data Directly (Without MCP)

This script bypasses the MCP server and connects directly to Confluence REST API.
Works with local Confluence Server/Data Center.

Usage:
    python scripts/collect_direct_confluence.py --url http://localhost:8090 --username admin --password admin
"""
import sys
import os
from pathlib import Path
import logging
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.mcp.confluence_direct_client import ConfluenceDirectClient
from app.mcp.confluence_collector import ConfluenceCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_from_local_confluence(
    base_url: str,
    username: str,
    password: str,
    spaces: list = None,
    max_pages: int = 100,
    verify_ssl: bool = True
):
    """
    Collect pages from local Confluence server

    Args:
        base_url: Confluence base URL (e.g., http://localhost:8090)
        username: Confluence username
        password: Confluence password
        spaces: List of space keys to collect (None = all spaces)
        max_pages: Maximum pages per space
        verify_ssl: Verify SSL certificates
    """
    logger.info("="*80)
    logger.info("Direct Confluence Data Collection")
    logger.info("="*80)
    logger.info(f"Confluence URL: {base_url}")
    logger.info(f"Username: {username}")
    logger.info(f"Max pages per space: {max_pages}")
    logger.info(f"Target spaces: {spaces if spaces else 'ALL'}")
    logger.info("="*80)

    # Initialize direct client
    logger.info("\n1. Initializing Confluence Client...")

    client = ConfluenceDirectClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_ssl=verify_ssl
    )

    # Test connection
    logger.info("\n2. Testing Connection...")
    if not client.test_connection():
        logger.error("✗ Connection failed!")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check if Confluence is running:")
        logger.info(f"   curl {base_url}")
        logger.info("2. Verify credentials are correct")
        logger.info("3. Check if REST API is enabled")
        logger.info("4. For local server, try: username='admin', password='admin'")
        return

    logger.info("✓ Connection successful!")

    # List spaces
    logger.info("\n3. Listing Spaces...")
    all_spaces = client.list_spaces()

    if not all_spaces:
        logger.warning("✗ No spaces found!")
        logger.info("\nThis could mean:")
        logger.info("1. Confluence is empty (no spaces created)")
        logger.info("2. User doesn't have permission to view spaces")
        logger.info(f"3. Go to {base_url} and create a space first")
        return

    logger.info(f"✓ Found {len(all_spaces)} space(s):")
    for space in all_spaces:
        space_key = space.get('key', 'N/A')
        space_name = space.get('name', 'N/A')
        space_type = space.get('type', 'N/A')
        logger.info(f"  - {space_key}: {space_name} ({space_type})")

    # Determine target spaces
    if spaces:
        target_spaces = spaces
    else:
        target_spaces = [s.get('key') for s in all_spaces if s.get('key')]

    logger.info(f"\n4. Collecting Pages from {len(target_spaces)} space(s)...")

    all_pages = []
    for space_key in target_spaces:
        logger.info(f"\n→ Space: {space_key}")

        try:
            pages = client.get_all_pages_from_space(
                space_key=space_key,
                max_pages=max_pages
            )

            if pages:
                logger.info(f"  ✓ Collected {len(pages)} pages")
                all_pages.extend(pages)

                # Show sample pages
                for i, page in enumerate(pages[:5], 1):
                    logger.info(f"    {i}. {page.title} (ID: {page.id}, Version: {page.version})")

                if len(pages) > 5:
                    logger.info(f"    ... and {len(pages) - 5} more pages")
            else:
                logger.warning(f"  ✗ No pages found in {space_key}")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")

    if not all_pages:
        logger.warning("\n⚠ No pages collected!")
        logger.info(f"\nGo to {base_url} and create some pages first.")
        return

    # Save to database
    logger.info("\n5. Saving to Database...")

    # Create a mock MCP client (not used, but required by ConfluenceCollector)
    from unittest.mock import Mock
    mock_mcp_client = Mock()

    db_path = str(project_root / "app" / "data" / "cache" / "confluence_direct.db")
    collector = ConfluenceCollector(mock_mcp_client, db_path)

    try:
        saved_count = collector.save_to_cache(all_pages)
        logger.info(f"✓ Saved {saved_count} pages")
    except Exception as e:
        logger.error(f"✗ Failed to save: {e}")
        return

    # Show statistics
    logger.info("\n6. Collection Statistics...")
    stats = collector.get_collection_stats()

    logger.info(f"\n📊 Summary:")
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
    logger.info("✓ Collection Completed Successfully!")
    logger.info("="*80)
    logger.info(f"\nDatabase: {db_path}")
    logger.info("You can now use this data for RAG indexing.")
    logger.info("\nNext steps:")
    logger.info("  python scripts/build_index.py --source confluence")


def main():
    parser = argparse.ArgumentParser(
        description="Collect Confluence data directly (without MCP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default Confluence setup)
  python scripts/collect_direct_confluence.py \\
    --url http://localhost:8090 \\
    --username admin \\
    --password admin

  # Collect from specific spaces
  python scripts/collect_direct_confluence.py \\
    --url http://localhost:8090 \\
    --username admin \\
    --password admin \\
    --spaces MY_TEST CS TECH

  # Collect more pages
  python scripts/collect_direct_confluence.py \\
    --url http://localhost:8090 \\
    --username admin \\
    --password admin \\
    --max-pages 200

  # For self-signed SSL certificates
  python scripts/collect_direct_confluence.py \\
    --url https://confluence.example.com \\
    --username admin \\
    --password admin \\
    --no-verify-ssl

Prerequisites:
  1. Confluence server must be running
  2. You need valid Confluence credentials
  3. User must have permission to view spaces and pages

Default Confluence Setup:
  URL: http://localhost:8090
  Username: admin
  Password: admin (or whatever you set during setup)
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Confluence base URL (e.g., http://localhost:8090)"
    )

    parser.add_argument(
        "--username",
        required=True,
        help="Confluence username"
    )

    parser.add_argument(
        "--password",
        required=True,
        help="Confluence password"
    )

    parser.add_argument(
        "--spaces",
        nargs="+",
        help="Space keys to collect from (default: all spaces)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum pages per space (default: 100)"
    )

    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (for self-signed certs)"
    )

    args = parser.parse_args()

    # Run collection
    collect_from_local_confluence(
        base_url=args.url,
        username=args.username,
        password=args.password,
        spaces=args.spaces,
        max_pages=args.max_pages,
        verify_ssl=not args.no_verify_ssl
    )


if __name__ == "__main__":
    main()
