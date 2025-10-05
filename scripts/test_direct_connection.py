"""
Test Direct Confluence Connection

Quick test to verify direct Confluence REST API connection works.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.mcp.confluence_direct_client import ConfluenceDirectClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection(base_url: str, username: str, password: str):
    """Test Confluence direct connection"""

    print("="*80)
    print("Testing Direct Confluence Connection")
    print("="*80)
    print()
    print(f"URL: {base_url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print()
    print("="*80)

    # Initialize client
    print("\n1. Initializing client...")
    client = ConfluenceDirectClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_ssl=False  # For local development
    )
    print("   [OK] Client initialized")

    # Test connection
    print("\n2. Testing connection...")
    if not client.test_connection():
        print("   [FAILED] Connection test failed")
        print("\nTroubleshooting:")
        print("1. Is Confluence running?")
        print(f"   Try: curl {base_url}")
        print("2. Are credentials correct?")
        print("3. Is REST API enabled?")
        return False

    print("   [OK] Connection successful")

    # List spaces
    print("\n3. Listing spaces...")
    spaces = client.list_spaces(limit=10)

    if not spaces:
        print("   [WARN] No spaces found")
        print(f"\n   Go to {base_url} and create a space first:")
        print("   1. Click 'Create' → 'Space'")
        print("   2. Enter space name and key")
        print("   3. Create some pages")
        return True

    print(f"   [OK] Found {len(spaces)} space(s):")
    for space in spaces:
        print(f"      - {space.get('key')}: {space.get('name')}")

    # Get pages from first space
    if spaces:
        first_space_key = spaces[0].get('key')
        print(f"\n4. Getting pages from space '{first_space_key}'...")

        pages = client.get_all_pages_from_space(
            space_key=first_space_key,
            max_pages=5
        )

        if not pages:
            print(f"   [WARN] No pages found in space '{first_space_key}'")
            print(f"\n   Go to {base_url} and create some pages:")
            print(f"   1. Navigate to space '{first_space_key}'")
            print("   2. Click 'Create' → 'Page'")
            print("   3. Add content and publish")
        else:
            print(f"   [OK] Found {len(pages)} page(s):")
            for i, page in enumerate(pages, 1):
                print(f"      {i}. {page.title}")
                print(f"         ID: {page.id}, Version: {page.version}")
                print(f"         Created: {page.created}")
                print(f"         Content length: {len(page.content)} chars")

    print("\n" + "="*80)
    print("✓ Connection Test Completed Successfully!")
    print("="*80)
    print("\nYou can now collect data with:")
    print(f"  python scripts/collect_direct_confluence.py \\")
    print(f"    --url {base_url} \\")
    print(f"    --username {username} \\")
    print(f"    --password {password}")
    print()

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test direct Confluence connection"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8090",
        help="Confluence base URL (default: http://localhost:8090)"
    )

    parser.add_argument(
        "--username",
        default="admin",
        help="Confluence username (default: admin)"
    )

    parser.add_argument(
        "--password",
        default="admin",
        help="Confluence password (default: admin)"
    )

    args = parser.parse_args()

    success = test_connection(
        base_url=args.url,
        username=args.username,
        password=args.password
    )

    sys.exit(0 if success else 1)
