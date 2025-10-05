"""
Unit Tests for Jira Collector

Tests for Jira data collection and SQLite caching
"""
import pytest
import sqlite3
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp.jira_collector import JiraCollector
from app.mcp.types import JiraIssue


class TestJiraCollectorInitialization:
    """JiraCollector initialization tests"""

    def test_init_creates_database(self):
        """Database is created on initialization"""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmpdir, "test.db")
            mock_client = Mock()

            collector = JiraCollector(mock_client, db_path)

            assert os.path.exists(db_path)
            assert collector.db_path == db_path
            assert collector.batch_size == 50

            # Close any open connections
            del collector
        finally:
            # Cleanup
            import shutil
            import time
            time.sleep(0.1)  # Give time for file handles to close
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

            collector = JiraCollector(mock_client, db_path)

            # Verify tables exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='jira_issues'
                """)
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == 'jira_issues'

            # Close collector
            del collector
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass


class TestJiraCollectorDataCollection:
    """Data collection tests"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        yield db_path
        # Cleanup after test
        import shutil
        import time
        time.sleep(0.1)  # Give time for connections to close
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def mock_client(self):
        """Create mock MCP client"""
        client = Mock()
        return client

    @pytest.fixture
    def sample_issues(self):
        """Create sample Jira issues"""
        return [
            JiraIssue(
                key="PROJ-1",
                summary="Test issue 1",
                description="Description 1",
                status="Done",
                priority="High",
                assignee="user1",
                reporter="user2",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 15),
                issue_type="Bug",
                labels=["bug", "critical"],
                components=["backend"]
            ),
            JiraIssue(
                key="PROJ-2",
                summary="Test issue 2",
                description="Description 2",
                status="In Progress",
                priority="Medium",
                assignee="user3",
                reporter="user1",
                created=datetime(2024, 1, 2),
                updated=datetime(2024, 1, 16),
                issue_type="Feature",
                labels=["feature"],
                components=["frontend"]
            ),
        ]

    def test_collect_issues_success(self, temp_db, mock_client, sample_issues):
        """Successfully collect and save issues"""
        mock_client.search_jira_issues.return_value = sample_issues

        collector = JiraCollector(mock_client, temp_db)
        issues = collector.collect_issues(jql="project = PROJ", max_results=100)

        assert len(issues) == 2
        assert issues[0].key == "PROJ-1"
        assert issues[1].key == "PROJ-2"

        # Verify MCP client was called
        mock_client.search_jira_issues.assert_called_once()

    def test_collect_issues_with_project_filter(self, temp_db, mock_client, sample_issues):
        """Collect issues with project filter"""
        mock_client.search_jira_issues.return_value = sample_issues

        collector = JiraCollector(mock_client, temp_db)
        issues = collector.collect_issues(project="PROJ", max_results=100)

        assert len(issues) == 2

        # Verify JQL was built correctly
        call_args = mock_client.search_jira_issues.call_args
        assert "project = PROJ" in call_args.kwargs['jql']

    def test_get_issue_details(self, temp_db, mock_client, sample_issues):
        """Get single issue details"""
        mock_client.get_jira_issue.return_value = sample_issues[0]

        collector = JiraCollector(mock_client, temp_db)
        issue = collector.get_issue_details("PROJ-1")

        assert issue is not None
        assert issue.key == "PROJ-1"
        assert issue.summary == "Test issue 1"

        mock_client.get_jira_issue.assert_called_once_with("PROJ-1")


class TestJiraCollectorCaching:
    """SQLite caching tests"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
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
        """Create collector with temp database"""
        mock_client = Mock()
        return JiraCollector(mock_client, temp_db)

    @pytest.fixture
    def sample_issues(self):
        """Create sample issues"""
        return [
            JiraIssue(
                key="PROJ-100",
                summary="Cached issue",
                status="Done",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                issue_type="Bug",
                labels=["test"],
                components=[]
            )
        ]

    def test_save_to_cache(self, collector, sample_issues):
        """Issues are saved to cache"""
        saved_count = collector.save_to_cache(sample_issues)

        assert saved_count == 1

        # Verify data in database
        with sqlite3.connect(collector.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jira_issues WHERE issue_key = ?", ("PROJ-100",))
            row = cursor.fetchone()

            assert row is not None
            # issue_key is first column
            assert row[0] == "PROJ-100"

    def test_save_to_cache_batch_processing(self, collector):
        """Batch processing works correctly"""
        # Create 150 issues (3 batches of 50)
        issues = [
            JiraIssue(
                key=f"PROJ-{i}",
                summary=f"Issue {i}",
                status="Done",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                issue_type="Bug",
                labels=[],
                components=[]
            )
            for i in range(150)
        ]

        saved_count = collector.save_to_cache(issues)

        assert saved_count == 150

        # Verify all saved
        with sqlite3.connect(collector.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM jira_issues")
            count = cursor.fetchone()[0]
            assert count == 150

    def test_save_to_cache_upsert(self, collector, sample_issues):
        """Saving same issue twice updates it (UPSERT)"""
        # Save first time
        collector.save_to_cache(sample_issues)

        # Modify and save again
        sample_issues[0].summary = "Updated summary"
        collector.save_to_cache(sample_issues)

        # Verify only one record exists with updated data
        with sqlite3.connect(collector.db_path) as conn:
            cursor = conn.execute("SELECT summary FROM jira_issues WHERE issue_key = ?", ("PROJ-100",))
            row = cursor.fetchone()

            assert row[0] == "Updated summary"

            # Verify count is still 1
            cursor = conn.execute("SELECT COUNT(*) FROM jira_issues")
            assert cursor.fetchone()[0] == 1

    def test_save_to_cache_error_handling(self, collector):
        """Errors in single issue don't stop batch"""
        issues = [
            JiraIssue(
                key=f"PROJ-{i}",
                summary=f"Issue {i}",
                status="Done",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                issue_type="Bug",
                labels=[],
                components=[]
            )
            for i in range(5)
        ]

        # Mock to simulate error on one issue
        with patch.object(collector, '_save_single_issue') as mock_save:
            # Make second call raise exception
            mock_save.side_effect = [
                None,  # Success
                Exception("Test error"),  # Failure
                None,  # Success
                None,  # Success
                None,  # Success
            ]

            # Should continue despite error
            saved_count = collector.save_to_cache(issues)

            # All issues attempted (errors are logged but don't increment count)
            assert mock_save.call_count == 5


class TestJiraCollectorIncrementalUpdate:
    """Incremental update tests"""

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

    def test_incremental_update(self, temp_db, mock_client):
        """Incremental update fetches recent issues"""
        recent_issues = [
            JiraIssue(
                key="PROJ-10",
                summary="Recent issue",
                status="Done",
                created=datetime(2024, 1, 1),
                updated=datetime.now(),
                issue_type="Bug",
                labels=[],
                components=[]
            )
        ]

        mock_client.search_jira_issues.return_value = recent_issues

        collector = JiraCollector(mock_client, temp_db)
        issues = collector.incremental_update(since_hours=24)

        assert len(issues) == 1

        # Verify JQL contains time filter
        call_args = mock_client.search_jira_issues.call_args
        jql = call_args.kwargs['jql']
        assert "updated >= -24h" in jql

    def test_get_last_sync_time(self, temp_db, mock_client):
        """Get last sync time from database"""
        collector = JiraCollector(mock_client, temp_db)

        # Initially no sync
        last_sync = collector.get_last_sync_time()
        assert last_sync is None

        # After saving an issue
        issues = [
            JiraIssue(
                key="PROJ-1",
                summary="Test",
                status="Done",
                created=datetime(2024, 1, 1),
                updated=datetime(2024, 1, 10),
                issue_type="Bug",
                labels=[],
                components=[]
            )
        ]
        collector.save_to_cache(issues)

        # Should have sync time
        last_sync = collector.get_last_sync_time()
        assert last_sync is not None


class TestJiraCollectorStats:
    """Statistics and query tests"""

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
        collector = JiraCollector(mock_client, temp_db)

        # Add test data
        issues = [
            JiraIssue(
                key=f"PROJ-{i}",
                summary=f"Issue {i}",
                status="Done" if i % 2 == 0 else "In Progress",
                created=datetime(2024, 1, i % 28 + 1),
                updated=datetime(2024, 1, i % 28 + 1),
                issue_type="Bug",
                labels=[],
                components=[]
            )
            for i in range(10)
        ]
        collector.save_to_cache(issues)

        return collector

    def test_get_collection_stats(self, collector_with_data):
        """Collection statistics are correct"""
        stats = collector_with_data.get_collection_stats()

        assert stats['total_issues'] == 10
        assert 'Done' in stats['status_distribution']
        assert 'In Progress' in stats['status_distribution']
        assert stats['status_distribution']['Done'] == 5
        assert stats['status_distribution']['In Progress'] == 5
        assert stats['last_sync'] is not None

    def test_get_cached_issues(self, collector_with_data):
        """Retrieve cached issues"""
        issues = collector_with_data.get_cached_issues(limit=5)

        assert len(issues) == 5
        assert all('issue_key' in issue for issue in issues)

    def test_get_cached_issues_with_filter(self, collector_with_data):
        """Filter cached issues by status"""
        issues = collector_with_data.get_cached_issues(status="Done", limit=10)

        assert len(issues) == 5
        assert all(issue['status'] == 'Done' for issue in issues)

    def test_clear_cache(self, collector_with_data):
        """Clear cache removes all data"""
        # Verify data exists
        stats = collector_with_data.get_collection_stats()
        assert stats['total_issues'] == 10

        # Clear cache
        collector_with_data.clear_cache()

        # Verify data is gone
        stats = collector_with_data.get_collection_stats()
        assert stats['total_issues'] == 0


class TestJiraCollectorJQLBuilder:
    """JQL query builder tests"""

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

    def test_default_jql(self, temp_db):
        """Default JQL query is generated"""
        mock_client = Mock()
        collector = JiraCollector(mock_client, temp_db)

        jql = collector._build_default_jql()

        assert "Done" in jql or "Resolved" in jql
        assert "ORDER BY" in jql

    def test_jql_with_project(self, temp_db):
        """JQL includes project filter"""
        mock_client = Mock()
        collector = JiraCollector(mock_client, temp_db)

        jql = collector._build_default_jql(project="MYPROJECT")

        assert "project = MYPROJECT" in jql

    def test_jql_with_status(self, temp_db):
        """JQL includes status filter"""
        mock_client = Mock()
        collector = JiraCollector(mock_client, temp_db)

        jql = collector._build_default_jql(status="Done")

        assert "status = 'Done'" in jql


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
