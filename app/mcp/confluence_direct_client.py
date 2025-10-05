"""
Direct Confluence REST API Client

This client connects directly to Confluence server without MCP.
Works with both Confluence Cloud and self-hosted Confluence Server/Data Center.
"""
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from requests.auth import HTTPBasicAuth
from .types import ConfluencePage

logger = logging.getLogger(__name__)


class ConfluenceDirectClient:
    """Direct Confluence REST API client"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ):
        """
        Initialize Confluence Direct Client

        Args:
            base_url: Confluence base URL (e.g., http://localhost:8090/confluence)
            username: Confluence username
            password: Confluence password or API token
            verify_ssl: Verify SSL certificates (set False for self-signed certs)
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = verify_ssl

        # For self-hosted Confluence, API is at /rest/api
        # For Cloud, it's at /wiki/rest/api
        if '/wiki' in base_url:
            self.api_base = f"{base_url}/rest/api"
        else:
            self.api_base = f"{base_url}/rest/api"

        logger.info(f"ConfluenceDirectClient initialized: {self.api_base}")

    def test_connection(self) -> bool:
        """
        Test connection to Confluence server

        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{self.api_base}/space"
            response = self.session.get(url, params={'limit': 1})
            response.raise_for_status()
            logger.info("✓ Confluence connection test successful")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Confluence connection test failed: {e}")
            return False

    def list_spaces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all Confluence spaces

        Args:
            limit: Maximum number of spaces to retrieve

        Returns:
            List of space dictionaries
        """
        try:
            url = f"{self.api_base}/space"
            params = {
                'limit': limit,
                'expand': 'description,homepage'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            spaces = data.get('results', [])
            logger.info(f"Found {len(spaces)} spaces")

            return spaces

        except Exception as e:
            logger.error(f"Failed to list spaces: {e}")
            return []

    def get_space_pages(
        self,
        space_key: str,
        limit: int = 100,
        start: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pages from a specific space

        Args:
            space_key: Space key (e.g., 'DS', 'TECH')
            limit: Maximum pages per request
            start: Starting index for pagination

        Returns:
            List of page dictionaries
        """
        try:
            url = f"{self.api_base}/space/{space_key}/content/page"
            params = {
                'limit': limit,
                'start': start,
                'expand': 'version,body.storage,space,history,metadata.labels'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get('results', [])
            logger.info(f"Retrieved {len(pages)} pages from space {space_key}")

            return pages

        except Exception as e:
            logger.error(f"Failed to get pages from space {space_key}: {e}")
            return []

    def get_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific page by ID

        Args:
            page_id: Confluence page ID

        Returns:
            Page dictionary or None
        """
        try:
            url = f"{self.api_base}/content/{page_id}"
            params = {
                'expand': 'version,body.storage,space,history,metadata.labels,ancestors'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()
            page = response.json()

            logger.info(f"Retrieved page {page_id}: {page.get('title', 'N/A')}")
            return page

        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None

    def search_pages(
        self,
        cql: str,
        limit: int = 100,
        start: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search pages using CQL (Confluence Query Language)

        Args:
            cql: CQL query string
            limit: Maximum results
            start: Starting index

        Returns:
            List of page dictionaries

        Example CQL queries:
            - "type=page AND space=DS"
            - "type=page AND lastModified >= now('-7d')"
            - "type=page AND text ~ 'customer support'"
        """
        try:
            url = f"{self.api_base}/content/search"
            params = {
                'cql': cql,
                'limit': limit,
                'start': start,
                'expand': 'version,body.storage,space,history,metadata.labels'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get('results', [])
            logger.info(f"Search found {len(pages)} pages")

            return pages

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _parse_page(self, page_data: Dict[str, Any]) -> ConfluencePage:
        """
        Parse raw Confluence API response to ConfluencePage object

        Args:
            page_data: Raw page data from Confluence API

        Returns:
            ConfluencePage object
        """
        # Extract basic info
        page_id = page_data.get('id', '')
        title = page_data.get('title', '')
        space_key = page_data.get('space', {}).get('key', '')

        # Extract body content
        body = page_data.get('body', {})
        storage = body.get('storage', {})
        content = storage.get('value', '')

        # Extract version info
        version_data = page_data.get('version', {})
        version = version_data.get('number', 1)

        # Extract history/dates
        history = page_data.get('history', {})
        created_by = history.get('createdBy', {}).get('displayName', 'Unknown')

        # Parse dates
        created_date_str = history.get('createdDate')
        created = self._parse_date(created_date_str) if created_date_str else datetime.now()

        version_when = version_data.get('when')
        updated = self._parse_date(version_when) if version_when else created

        # Extract labels
        metadata = page_data.get('metadata', {})
        labels_data = metadata.get('labels', {}).get('results', [])
        labels = [label.get('name', '') for label in labels_data if label.get('name')]

        # Extract author
        version_by = version_data.get('by', {})
        author = version_by.get('displayName', created_by)

        return ConfluencePage(
            id=page_id,
            title=title,
            space=space_key,
            content=content,
            version=version,
            created=created,
            updated=updated,
            author=author,
            labels=labels
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse Confluence date string to datetime"""
        try:
            # Confluence uses ISO 8601 format
            # Example: "2024-10-04T10:30:00.000Z"
            if 'T' in date_str:
                # Remove timezone info for simplicity
                date_str = date_str.split('+')[0].split('Z')[0].split('.')[0]
                return datetime.fromisoformat(date_str)
            else:
                return datetime.now()
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.now()

    def get_all_pages_from_space(
        self,
        space_key: str,
        max_pages: int = 1000
    ) -> List[ConfluencePage]:
        """
        Get all pages from a space with pagination

        Args:
            space_key: Space key
            max_pages: Maximum pages to retrieve

        Returns:
            List of ConfluencePage objects
        """
        all_pages = []
        start = 0
        limit = 50  # Pages per request

        while len(all_pages) < max_pages:
            pages_data = self.get_space_pages(
                space_key=space_key,
                limit=limit,
                start=start
            )

            if not pages_data:
                break

            # Parse pages
            for page_data in pages_data:
                try:
                    page = self._parse_page(page_data)
                    all_pages.append(page)

                    if len(all_pages) >= max_pages:
                        break
                except Exception as e:
                    logger.error(f"Failed to parse page: {e}")

            # Check if there are more pages
            if len(pages_data) < limit:
                break

            start += limit

        logger.info(f"Retrieved total {len(all_pages)} pages from space {space_key}")
        return all_pages

    def get_all_pages(self, max_pages: int = 1000) -> List[ConfluencePage]:
        """
        Get all pages from all spaces

        Args:
            max_pages: Maximum pages to retrieve

        Returns:
            List of ConfluencePage objects
        """
        all_pages = []

        # Get all spaces
        spaces = self.list_spaces()

        for space in spaces:
            space_key = space.get('key')
            if not space_key:
                continue

            logger.info(f"Collecting pages from space: {space_key}")

            pages = self.get_all_pages_from_space(
                space_key=space_key,
                max_pages=max_pages - len(all_pages)
            )

            all_pages.extend(pages)

            if len(all_pages) >= max_pages:
                break

        return all_pages
