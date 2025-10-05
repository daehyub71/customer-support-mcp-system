"""
Data Collection Script

CLI tool for collecting Jira and Confluence data from MCP Server
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcp.mcp_client import MCPClient
from app.mcp.jira_collector import JiraCollector
from app.mcp.confluence_collector import ConfluenceCollector
from app.utils.config import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app/logs/collection.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def collect_jira_data(args):
    """Collect Jira issues"""
    logger.info("=" * 80)
    logger.info("Starting Jira Data Collection")
    logger.info("=" * 80)

    # Initialize MCP Client
    logger.info("Connecting to MCP Server...")
    mcp_client = MCPClient(
        host=args.mcp_host,
        port=args.mcp_port,
        timeout=args.timeout
    )

    try:
        # Connect to MCP server
        mcp_client.connect()

        # Initialize Jira Collector
        db_path = args.db_path or "app/data/cache/jira_cache.db"
        collector = JiraCollector(mcp_client, db_path)

        # Display current stats
        logger.info("\nCurrent cache statistics:")
        stats = collector.get_collection_stats()
        logger.info(f"  Total issues: {stats['total_issues']}")
        logger.info(f"  Last sync: {stats['last_sync']}")
        logger.info(f"  Status distribution: {stats['status_distribution']}")

        # Collect data
        if args.incremental:
            logger.info(f"\nPerforming incremental update (last {args.incremental} hours)...")
            issues = collector.incremental_update(since_hours=args.incremental)
        else:
            logger.info(f"\nCollecting issues with JQL: {args.jql}")
            issues = collector.collect_issues(
                jql=args.jql,
                max_results=args.limit,
                project=args.project,
                status=args.status
            )

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("Collection completed successfully!")
        logger.info(f"Issues collected: {len(issues)}")

        # Display updated stats
        logger.info("\nUpdated cache statistics:")
        stats = collector.get_collection_stats()
        logger.info(f"  Total issues: {stats['total_issues']}")
        logger.info(f"  Last sync: {stats['last_sync']}")
        logger.info(f"  Status distribution: {stats['status_distribution']}")

        # Show sample issues
        if issues and args.verbose:
            logger.info("\nSample issues:")
            for issue in issues[:5]:
                logger.info(f"  [{issue.key}] {issue.summary} ({issue.status})")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        mcp_client.disconnect()


def collect_confluence_data(args):
    """Collect Confluence pages"""
    logger.info("=" * 80)
    logger.info("Starting Confluence Data Collection")
    logger.info("=" * 80)

    # Initialize MCP Client
    logger.info("Connecting to MCP Server...")
    mcp_client = MCPClient(
        host=args.mcp_host,
        port=args.mcp_port,
        timeout=args.timeout
    )

    try:
        # Connect to MCP server
        mcp_client.connect()

        # Initialize Confluence Collector
        db_path = args.db_path or "app/data/cache/confluence_cache.db"
        collector = ConfluenceCollector(mcp_client, db_path)

        # Display current stats
        logger.info("\nCurrent cache statistics:")
        stats = collector.get_collection_stats()
        logger.info(f"  Total pages: {stats['total_pages']}")
        logger.info(f"  Total spaces: {stats['total_spaces']}")
        logger.info(f"  Last sync: {stats['last_sync']}")
        logger.info(f"  Space distribution: {stats['space_distribution']}")

        # Parse space keys if provided
        space_keys = None
        if args.spaces:
            space_keys = [s.strip() for s in args.spaces.split(',')]
            logger.info(f"\nCollecting from specific spaces: {space_keys}")
        elif args.space:
            space_keys = [args.space]
            logger.info(f"\nCollecting from space: {args.space}")

        # Collect data
        if args.incremental:
            logger.info(f"\nPerforming incremental update (last {args.incremental} hours)...")
            pages = collector.incremental_update(since_hours=args.incremental)
        else:
            logger.info(f"\nCollecting pages (max={args.limit})...")
            pages = collector.collect_pages(
                space_keys=space_keys,
                max_pages=args.limit
            )

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("Collection completed successfully!")
        logger.info(f"Pages collected: {len(pages)}")

        # Display updated stats
        logger.info("\nUpdated cache statistics:")
        stats = collector.get_collection_stats()
        logger.info(f"  Total pages: {stats['total_pages']}")
        logger.info(f"  Total spaces: {stats['total_spaces']}")
        logger.info(f"  Last sync: {stats['last_sync']}")
        logger.info(f"  Space distribution: {stats['space_distribution']}")

        # Show sample pages
        if pages and args.verbose:
            logger.info("\nSample pages:")
            for page in pages[:5]:
                logger.info(f"  [{page.id}] {page.title} (space: {page.space})")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        mcp_client.disconnect()


def show_stats(args):
    """Show collection statistics"""
    logger.info("Cache Statistics")
    logger.info("=" * 80)

    db_path = args.db_path or "app/data/cache/jira_cache.db"

    # Check if database exists
    if not Path(db_path).exists():
        logger.warning(f"Database not found: {db_path}")
        logger.info("Run collection first: python scripts/collect_data.py --source jira")
        return

    # Initialize collector (no MCP client needed for stats)
    from app.mcp.jira_collector import JiraCollector
    mcp_client = MCPClient()  # Dummy client
    collector = JiraCollector(mcp_client, db_path)

    stats = collector.get_collection_stats()

    logger.info(f"\nJira Issues Cache: {db_path}")
    logger.info(f"  Total issues: {stats['total_issues']}")
    logger.info(f"  Last sync: {stats['last_sync']}")
    logger.info(f"  Date range: {stats['date_range']['oldest']} to {stats['date_range']['newest']}")
    logger.info(f"\n  Status distribution:")
    for status, count in stats['status_distribution'].items():
        logger.info(f"    {status}: {count}")

    logger.info("=" * 80)


def clear_cache(args):
    """Clear cache data"""
    db_path = args.db_path or "app/data/cache/jira_cache.db"

    if not Path(db_path).exists():
        logger.warning(f"Database not found: {db_path}")
        return

    if not args.force:
        response = input("Are you sure you want to clear the cache? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cache clear cancelled")
            return

    logger.info(f"Clearing cache: {db_path}")

    from app.mcp.jira_collector import JiraCollector
    mcp_client = MCPClient()
    collector = JiraCollector(mcp_client, db_path)
    collector.clear_cache()

    logger.info("Cache cleared successfully")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Collect Jira/Confluence data from MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Jira: Collect issues with default JQL
  python scripts/collect_data.py --source jira

  # Jira: Collect with custom JQL
  python scripts/collect_data.py --source jira --jql "status = Done AND resolved >= -180d"

  # Jira: Collect specific project
  python scripts/collect_data.py --source jira --project PROJ --limit 500

  # Jira: Incremental update (last 24 hours)
  python scripts/collect_data.py --source jira --incremental 24

  # Confluence: Collect all pages
  python scripts/collect_data.py --source confluence

  # Confluence: Collect specific spaces
  python scripts/collect_data.py --source confluence --spaces CS,TECH,KB

  # Confluence: Incremental update
  python scripts/collect_data.py --source confluence --incremental 24

  # Show statistics
  python scripts/collect_data.py --stats

  # Clear cache
  python scripts/collect_data.py --clear-cache --force
        """
    )

    # Main arguments
    parser.add_argument('--source', choices=['jira', 'confluence'],
                       help='Data source to collect from')
    parser.add_argument('--stats', action='store_true',
                       help='Show cache statistics')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear cache data')

    # Jira-specific arguments
    jira_group = parser.add_argument_group('Jira options')
    jira_group.add_argument('--jql', type=str,
                           default="status IN (Done, Resolved, Closed) AND resolved >= -180d ORDER BY updated DESC",
                           help='JQL query string (default: closed issues in last 180 days)')
    jira_group.add_argument('--project', type=str,
                           help='Project key to filter')
    jira_group.add_argument('--status', type=str,
                           help='Status to filter')
    jira_group.add_argument('--limit', type=int, default=1000,
                           help='Maximum number of issues to collect (default: 1000)')
    jira_group.add_argument('--incremental', type=int, metavar='HOURS',
                           help='Incremental update: collect issues updated in last N hours')

    # Confluence-specific arguments
    confluence_group = parser.add_argument_group('Confluence options')
    confluence_group.add_argument('--spaces', type=str,
                                 help='Comma-separated list of space keys (e.g., CS,TECH,KB)')
    confluence_group.add_argument('--space', type=str,
                                 help='Single space key to collect from')

    # MCP Server options
    mcp_group = parser.add_argument_group('MCP Server options')
    mcp_group.add_argument('--mcp-host', type=str, default=config.MCP_SERVER_HOST,
                          help=f'MCP server host (default: {config.MCP_SERVER_HOST})')
    mcp_group.add_argument('--mcp-port', type=int, default=int(config.MCP_SERVER_PORT),
                          help=f'MCP server port (default: {config.MCP_SERVER_PORT})')
    mcp_group.add_argument('--timeout', type=int, default=30,
                          help='Request timeout in seconds (default: 30)')

    # Other options
    parser.add_argument('--db-path', type=str,
                       help='SQLite database path (default: app/data/cache/jira_cache.db)')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Ensure logs directory exists
    Path("app/logs").mkdir(parents=True, exist_ok=True)

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Route to appropriate function
    if args.stats:
        show_stats(args)
    elif args.clear_cache:
        clear_cache(args)
    elif args.source == 'jira':
        collect_jira_data(args)
    elif args.source == 'confluence':
        collect_confluence_data(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
