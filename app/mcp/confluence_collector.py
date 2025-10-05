"""
Confluence Data Collector

Confluence pages collection from MCP Server to SQLite cache
"""
import json
import logging
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup

from .mcp_client import MCPClient
from .types import ConfluencePage

logger = logging.getLogger(__name__)


class ConfluenceCollector:
    """Confluence data collector using MCP Client"""

    def __init__(self, mcp_client: MCPClient, db_path: str = "app/data/cache/confluence_cache.db"):
        """
        Initialize Confluence Collector

        Args:
            mcp_client: MCPClient instance
            db_path: SQLite database path
        """
        self.mcp_client = mcp_client
        self.db_path = db_path
        self.batch_size = 50

        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logger.info(f"ConfluenceCollector initialized with database: {db_path}")

    def _init_database(self):
        """Initialize SQLite database with schema"""
        schema_path = Path(__file__).parent.parent / "data" / "cache" / "schema.sql"

        try:
            with sqlite3.connect(self.db_path) as conn:
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                        conn.executescript(schema_sql)
                    logger.info("Database schema initialized from schema.sql")
                else:
                    logger.warning(f"Schema file not found: {schema_path}")
                    self._create_basic_schema(conn)

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _create_basic_schema(self, conn: sqlite3.Connection):
        """Create basic schema if schema.sql is not found"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS confluence_pages (
                page_id TEXT PRIMARY KEY,
                space_key TEXT NOT NULL,
                title TEXT NOT NULL,
                body_storage TEXT,
                body_view TEXT,
                body_cleaned TEXT,
                version INTEGER,
                creator TEXT,
                last_modifier TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                labels TEXT,
                url TEXT,
                raw_data TEXT,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_confluence_space_key ON confluence_pages(space_key)")
        logger.info("Basic Confluence schema created")

    def list_spaces(self) -> List[Dict[str, Any]]:
        """
        List all available Confluence spaces

        Returns:
            List of space dictionaries
        """
        logger.info("Listing Confluence spaces...")

        try:
            # Call MCP tool to list spaces
            response = self.mcp_client.call_tool("confluence_list_spaces", {})

            if response.isError:
                logger.error(f"Failed to list spaces: {response.content}")
                return []

            # Parse response
            spaces = []
            for item in response.content:
                if item.get("type") == "text":
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, list):
                            spaces.extend(data)
                        elif isinstance(data, dict):
                            spaces.append(data)
                    except Exception as e:
                        logger.warning(f"Failed to parse space data: {e}")

            logger.info(f"Found {len(spaces)} spaces")

            # Save spaces to cache
            if spaces:
                self._save_spaces_to_cache(spaces)

            return spaces

        except Exception as e:
            logger.error(f"Failed to list spaces: {e}")
            return []

    def _save_spaces_to_cache(self, spaces: List[Dict[str, Any]]):
        """Save spaces to cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for space in spaces:
                    conn.execute("""
                        INSERT OR REPLACE INTO confluence_spaces
                        (space_key, space_name, space_type, description, homepage_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        space.get('key'),
                        space.get('name'),
                        space.get('type'),
                        space.get('description'),
                        space.get('homepageId')
                    ))
                conn.commit()
                logger.info(f"Saved {len(spaces)} spaces to cache")

        except Exception as e:
            logger.error(f"Failed to save spaces: {e}")

    def list_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 100
    ) -> List[ConfluencePage]:
        """
        List pages from Confluence

        Args:
            space_key: Space key filter (optional)
            limit: Maximum pages to retrieve

        Returns:
            List of ConfluencePage objects
        """
        logger.info(f"Listing Confluence pages (space={space_key}, limit={limit})")

        try:
            # Build search query
            query = f"space = {space_key}" if space_key else "type = page"

            pages = self.mcp_client.search_confluence_pages(
                query=query,
                space=space_key,
                max_results=limit
            )

            logger.info(f"Retrieved {len(pages)} pages from MCP")

            return pages

        except Exception as e:
            logger.error(f"Failed to list pages: {e}")
            return []

    def get_page_content(self, page_id: str) -> Optional[ConfluencePage]:
        """
        Get detailed content for a specific page

        Args:
            page_id: Page ID

        Returns:
            ConfluencePage object or None
        """
        try:
            page = self.mcp_client.get_confluence_page(page_id)

            if page:
                logger.info(f"Retrieved page: {page_id}")

            return page

        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None

    def collect_pages(
        self,
        space_keys: Optional[List[str]] = None,
        max_pages: int = 1000
    ) -> List[ConfluencePage]:
        """
        Collect Confluence pages

        Args:
            space_keys: List of space keys to collect from (None = all spaces)
            max_pages: Maximum pages to collect

        Returns:
            List of ConfluencePage objects
        """
        logger.info(f"Starting Confluence page collection (max={max_pages})")

        all_pages = []

        try:
            # If no spaces specified, get all spaces
            if not space_keys:
                spaces = self.list_spaces()
                space_keys = [s.get('key') for s in spaces if s.get('key')]
                logger.info(f"Collecting from {len(space_keys)} spaces")

            # Collect pages from each space
            for space_key in space_keys:
                logger.info(f"Collecting pages from space: {space_key}")

                pages = self.list_pages(space_key=space_key, limit=max_pages)
                all_pages.extend(pages)

                logger.info(f"Collected {len(pages)} pages from {space_key}")

            # Save to cache
            if all_pages:
                saved_count = self.save_to_cache(all_pages)
                logger.info(f"Saved {saved_count} pages to cache")

            return all_pages

        except Exception as e:
            logger.error(f"Failed to collect pages: {e}")
            return all_pages

    def save_to_cache(self, pages: List[ConfluencePage]) -> int:
        """
        Save pages to SQLite cache with batch processing

        Args:
            pages: List of ConfluencePage objects

        Returns:
            Number of pages saved
        """
        if not pages:
            return 0

        saved_count = 0
        total_batches = (len(pages) + self.batch_size - 1) // self.batch_size

        logger.info(f"Saving {len(pages)} pages in {total_batches} batches")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Process in batches with progress bar
                for i in tqdm(range(0, len(pages), self.batch_size),
                             desc="Saving pages",
                             total=total_batches):
                    batch = pages[i:i + self.batch_size]

                    for page in batch:
                        try:
                            self._save_single_page(conn, page)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"Failed to save page {page.id}: {e}")
                            # Continue processing

                conn.commit()

        except Exception as e:
            logger.error(f"Database error during save: {e}")
            raise

        return saved_count

    def _save_single_page(self, conn: sqlite3.Connection, page: ConfluencePage):
        """Save a single page to database with HTML cleanup"""
        # Clean HTML content
        body_cleaned = None
        if page.content:
            body_cleaned = self.clean_html(page.content)

        # Convert lists to JSON
        labels_json = json.dumps(page.labels) if page.labels else "[]"
        raw_data_json = page.model_dump_json()

        conn.execute("""
            INSERT OR REPLACE INTO confluence_pages (
                page_id, space_key, title, body_storage, body_view, body_cleaned,
                version, creator, last_modifier, created_at, updated_at,
                labels, url, raw_data, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            page.id,
            page.space,
            page.title,
            page.content,  # Original HTML (body_storage)
            page.content,  # View HTML (same as storage for now)
            body_cleaned,  # Cleaned text
            page.version,
            page.author,
            page.author,  # last_modifier (using author for now)
            page.created,
            page.updated,
            labels_json,
            None,  # url - will be constructed from base URL
            raw_data_json,
        ))

    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content using BeautifulSoup4

        Args:
            html_content: Raw HTML string

        Returns:
            Cleaned text content
        """
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script tags
            for script in soup.find_all('script'):
                script.decompose()

            # Remove style tags
            for style in soup.find_all('style'):
                style.decompose()

            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                comment.extract()

            # Remove unnecessary attributes (keep only essential ones)
            for tag in soup.find_all(True):
                # Keep only class, id, href for essential navigation
                allowed_attrs = ['class', 'id', 'href']
                attrs_to_remove = [attr for attr in tag.attrs if attr not in allowed_attrs]
                for attr in attrs_to_remove:
                    del tag[attr]

            # Get text content
            text = soup.get_text(separator=' ', strip=True)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()

            return text

        except Exception as e:
            logger.error(f"Failed to clean HTML: {e}")
            return html_content

    def incremental_update(self, since_hours: int = 24) -> List[ConfluencePage]:
        """
        Perform incremental update - fetch recently updated pages

        Args:
            since_hours: Fetch pages updated in last N hours

        Returns:
            List of updated pages
        """
        logger.info(f"Starting incremental update (last {since_hours} hours)")

        try:
            # Build query for recent updates
            query = f"lastmodified >= now('-{since_hours}h')"

            pages = self.mcp_client.search_confluence_pages(
                query=query,
                max_results=1000
            )

            logger.info(f"Incremental update: found {len(pages)} updated pages")

            if pages:
                self.save_to_cache(pages)

            return pages

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return []

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync time from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT MAX(last_synced_at) FROM confluence_pages
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    return datetime.fromisoformat(result[0])

        except Exception as e:
            logger.error(f"Failed to get last sync time: {e}")

        return None

    def get_cached_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve cached pages from database

        Args:
            space_key: Filter by space key
            limit: Maximum results

        Returns:
            List of page dictionaries
        """
        query = "SELECT * FROM confluence_pages"
        params = []

        if space_key:
            query += " WHERE space_key = ?"
            params.append(space_key)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve cached pages: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        stats = {
            "total_pages": 0,
            "total_spaces": 0,
            "last_sync": None,
            "space_distribution": {},
            "date_range": {"oldest": None, "newest": None}
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total pages
                cursor = conn.execute("SELECT COUNT(*) FROM confluence_pages")
                stats["total_pages"] = cursor.fetchone()[0]

                # Total spaces
                cursor = conn.execute("SELECT COUNT(DISTINCT space_key) FROM confluence_pages")
                stats["total_spaces"] = cursor.fetchone()[0]

                # Last sync
                cursor = conn.execute("SELECT MAX(last_synced_at) FROM confluence_pages")
                result = cursor.fetchone()
                if result[0]:
                    stats["last_sync"] = result[0]

                # Space distribution
                cursor = conn.execute("""
                    SELECT space_key, COUNT(*) as count
                    FROM confluence_pages
                    GROUP BY space_key
                    ORDER BY count DESC
                """)
                stats["space_distribution"] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }

                # Date range
                cursor = conn.execute("""
                    SELECT MIN(created_at), MAX(updated_at)
                    FROM confluence_pages
                """)
                oldest, newest = cursor.fetchone()
                stats["date_range"] = {"oldest": oldest, "newest": newest}

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")

        return stats

    def clear_cache(self):
        """Clear all cached data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM confluence_pages")
                conn.execute("DELETE FROM confluence_spaces")
                conn.commit()
            logger.info("Confluence cache cleared successfully")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise
