"""
Unit Tests for Confluence Collector

Tests for Confluence page collection and HTML cleanup
"""
import pytest
import sqlite3
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp.confluence_collector import ConfluenceCollector
from app.mcp.types import ConfluencePage


class TestConfluenceCollectorInitialization:
    """ConfluenceCollector initialization tests"""

    def test_init_creates_database(self):
        """Database is created on initialization"""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmpdir, "test.db")
            mock_client = Mock()

            collector = ConfluenceCollector(mock_client, db_path)

            assert os.path.exists(db_path)
            assert collector.db_path == db_path
            assert collector.batch_size == 50

            del collector
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass

    def test_init_creates_schema(self):
        """Schema tables are created"""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmpdir, "test.db")
            mock_client = Mock()

            collector = ConfluenceCollector(mock_client, db_path)

            # Verify tables exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='confluence_pages'
                """)
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == 'confluence_pages'

            del collector
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass


class TestConfluenceCollectorSpaces:
    """Space listing tests"""

    @pytest.fixture
    def temp_db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        import shutil
        import time
        time.sleep(0.1)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def mock_client(self):
        return Mock()

    def test_list_spaces_success(self, temp_db, mock_client):
        """Successfully list Confluence spaces"""
        # Mock MCP response
        mock_response = Mock()
        mock_response.isError = False
        mock_response.content = [
            {
                "type": "text",
                "text": json.dumps([
                    {"key": "CS", "name": "Customer Support", "type": "global"},
                    {"key": "TECH", "name": "Technical Docs", "type": "global"}
                ])
            }
        ]
        mock_client.call_tool.return_value = mock_response

        collector = ConfluenceCollector(mock_client, temp_db)
        spaces = collector.list_spaces()

        assert len(spaces) == 2
        assert spaces[0]["key"] == "CS"
        assert spaces[1]["key"] == "TECH"

        mock_client.call_tool.assert_called_once()

    def test_list_spaces_saves_to_cache(self, temp_db, mock_client):
        """Spaces are saved to cache"""
        mock_response = Mock()
        mock_response.isError = False
        mock_response.content = [
            {
                "type": "text",
                "text": json.dumps([{"key": "TEST", "name": "Test Space", "type": "global"}])
            }
        ]
        mock_client.call_tool.return_value = mock_response

        collector = ConfluenceCollector(mock_client, temp_db)
        collector.list_spaces()

        # Verify space is in database
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT * FROM confluence_spaces WHERE space_key = ?", ("TEST",))
            row = cursor.fetchone()
            assert row is not None


class TestConfluenceCollectorPages:
    """Page collection tests"""

    @pytest.fixture
    def temp_db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        import shutil
        import time
        time.sleep(0.1)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def mock_client(self):
        return Mock()

    @pytest.fixture
    def sample_pages(self):
        return [
            ConfluencePage(
                id="12345",
                title="Test Page 1",
                space="CS",
                content="<p>Test content</p>",
                version=1,
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 15),
                author="user1",
                labels=["test", "docs"]
            ),
            ConfluencePage(
                id="67890",
                title="Test Page 2",
                space="TECH",
                content="<h1>Header</h1><p>More content</p>",
                version=2,
                created=datetime(2024, 1, 2),
                updated=datetime(2024, 1, 16),
                author="user2",
                labels=["technical"]
            )
        ]

    def test_list_pages_success(self, temp_db, mock_client, sample_pages):
        """Successfully list pages"""
        mock_client.search_confluence_pages.return_value = sample_pages

        collector = ConfluenceCollector(mock_client, temp_db)
        pages = collector.list_pages(space_key="CS", limit=100)

        assert len(pages) == 2
        mock_client.search_confluence_pages.assert_called_once()

    def test_get_page_content(self, temp_db, mock_client, sample_pages):
        """Get single page content"""
        mock_client.get_confluence_page.return_value = sample_pages[0]

        collector = ConfluenceCollector(mock_client, temp_db)
        page = collector.get_page_content("12345")

        assert page is not None
        assert page.id == "12345"
        assert page.title == "Test Page 1"


class TestConfluenceCollectorCaching:
    """Caching tests"""

    @pytest.fixture
    def temp_db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        import shutil
        import time
        time.sleep(0.1)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def collector(self, temp_db):
        mock_client = Mock()
        return ConfluenceCollector(mock_client, temp_db)

    @pytest.fixture
    def sample_pages(self):
        return [
            ConfluencePage(
                id="PAGE-100",
                title="Cached page",
                space="CS",
                content="<p>Test</p>",
                version=1,
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                author="user1",
                labels=["test"]
            )
        ]

    def test_save_to_cache(self, collector, sample_pages):
        """Pages are saved to cache"""
        saved_count = collector.save_to_cache(sample_pages)

        assert saved_count == 1

        # Verify data in database
        with sqlite3.connect(collector.db_path) as conn:
            cursor = conn.execute("SELECT * FROM confluence_pages WHERE page_id = ?", ("PAGE-100",))
            row = cursor.fetchone()
            assert row is not None

    def test_save_to_cache_batch_processing(self, collector):
        """Batch processing works correctly"""
        # Create 150 pages (3 batches of 50)
        pages = [
            ConfluencePage(
                id=f"PAGE-{i}",
                title=f"Page {i}",
                space="CS",
                content=f"<p>Content {i}</p>",
                version=1,
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                author="user1",
                labels=[]
            )
            for i in range(150)
        ]

        saved_count = collector.save_to_cache(pages)

        assert saved_count == 150

        # Verify all saved
        with sqlite3.connect(collector.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM confluence_pages")
            count = cursor.fetchone()[0]
            assert count == 150


class TestConfluenceCollectorHTMLCleaning:
    """HTML cleanup tests"""

    @pytest.fixture
    def temp_db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        import shutil
        import time
        time.sleep(0.1)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    def test_clean_html_removes_scripts(self, temp_db):
        """Scripts are removed from HTML"""
        mock_client = Mock()
        collector = ConfluenceCollector(mock_client, temp_db)

        html = "<p>Text</p><script>alert('test')</script><p>More text</p>"
        cleaned = collector.clean_html(html)

        assert "script" not in cleaned.lower()
        assert "alert" not in cleaned.lower()
        assert "Text" in cleaned
        assert "More text" in cleaned

    def test_clean_html_removes_styles(self, temp_db):
        """Styles are removed from HTML"""
        mock_client = Mock()
        collector = ConfluenceCollector(mock_client, temp_db)

        html = "<p>Text</p><style>.class { color: red; }</style><p>More</p>"
        cleaned = collector.clean_html(html)

        assert "style" not in cleaned.lower()
        assert "color" not in cleaned.lower()
        assert "Text" in cleaned

    def test_clean_html_normalizes_whitespace(self, temp_db):
        """Whitespace is normalized"""
        mock_client = Mock()
        collector = ConfluenceCollector(mock_client, temp_db)

        html = "<p>Text   with    multiple     spaces</p>"
        cleaned = collector.clean_html(html)

        # Multiple spaces should be collapsed
        assert "   " not in cleaned

    def test_clean_html_extracts_text(self, temp_db):
        """Text is extracted from HTML"""
        mock_client = Mock()
        collector = ConfluenceCollector(mock_client, temp_db)

        html = "<div><h1>Title</h1><p>Paragraph with <b>bold</b> text</p></div>"
        cleaned = collector.clean_html(html)

        assert "Title" in cleaned
        assert "Paragraph" in cleaned
        assert "bold" in cleaned


class TestConfluenceCollectorStats:
    """Statistics tests"""

    @pytest.fixture
    def temp_db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        import shutil
        import time
        time.sleep(0.1)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def collector_with_data(self, temp_db):
        """Collector with test data"""
        mock_client = Mock()
        collector = ConfluenceCollector(mock_client, temp_db)

        # Add test data
        pages = [
            ConfluencePage(
                id=f"PAGE-{i}",
                title=f"Page {i}",
                space="CS" if i % 2 == 0 else "TECH",
                content=f"<p>Content {i}</p>",
                version=1,
                created=datetime(2024, 1, i % 28 + 1),
                updated=datetime(2024, 1, i % 28 + 1),
                author="user1",
                labels=[]
            )
            for i in range(10)
        ]
        collector.save_to_cache(pages)

        return collector

    def test_get_collection_stats(self, collector_with_data):
        """Collection statistics are correct"""
        stats = collector_with_data.get_collection_stats()

        assert stats['total_pages'] == 10
        assert stats['total_spaces'] == 2
        assert 'CS' in stats['space_distribution']
        assert 'TECH' in stats['space_distribution']
        assert stats['space_distribution']['CS'] == 5
        assert stats['space_distribution']['TECH'] == 5

    def test_get_cached_pages(self, collector_with_data):
        """Retrieve cached pages"""
        pages = collector_with_data.get_cached_pages(limit=5)

        assert len(pages) == 5
        assert all('page_id' in page for page in pages)

    def test_get_cached_pages_with_filter(self, collector_with_data):
        """Filter cached pages by space"""
        pages = collector_with_data.get_cached_pages(space_key="CS", limit=10)

        assert len(pages) == 5
        assert all(page['space_key'] == 'CS' for page in pages)

    def test_clear_cache(self, collector_with_data):
        """Clear cache removes all data"""
        stats = collector_with_data.get_collection_stats()
        assert stats['total_pages'] == 10

        collector_with_data.clear_cache()

        stats = collector_with_data.get_collection_stats()
        assert stats['total_pages'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
