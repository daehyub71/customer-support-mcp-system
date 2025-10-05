"""
Jira Data Collector

Jira issues and comments collection from MCP Server to SQLite cache
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm

from .mcp_client import MCPClient
from .types import JiraIssue

logger = logging.getLogger(__name__)


class JiraCollector:
    """Jira data collector using MCP Client"""

    def __init__(self, mcp_client: MCPClient, db_path: str = "app/data/cache/jira_cache.db"):
        """
        Initialize Jira Collector

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

        logger.info(f"JiraCollector initialized with database: {db_path}")

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
                    # Fallback: create basic schema
                    self._create_basic_schema(conn)

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _create_basic_schema(self, conn: sqlite3.Connection):
        """Create basic schema if schema.sql is not found"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jira_issues (
                issue_key TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                description TEXT,
                status TEXT,
                issue_type TEXT,
                priority TEXT,
                assignee TEXT,
                reporter TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                resolved_at DATETIME,
                labels TEXT,
                components TEXT,
                raw_data TEXT,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jira_updated_at ON jira_issues(updated_at)")
        logger.info("Basic schema created")

    def collect_issues(
        self,
        jql: Optional[str] = None,
        max_results: int = 1000,
        project: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[JiraIssue]:
        """
        Collect Jira issues using MCP client

        Args:
            jql: JQL query string
            max_results: Maximum results to collect
            project: Project key filter
            status: Status filter

        Returns:
            List of JiraIssue objects
        """
        logger.info(f"Starting Jira collection (max_results={max_results})")

        # Build JQL if not provided
        if not jql:
            jql = self._build_default_jql(project, status)

        logger.info(f"Using JQL: {jql}")

        try:
            # Collect issues from MCP
            issues = self.mcp_client.search_jira_issues(
                jql=jql,
                max_results=max_results
            )

            logger.info(f"Collected {len(issues)} issues from MCP")

            # Save to cache
            if issues:
                saved_count = self.save_to_cache(issues)
                logger.info(f"Saved {saved_count} issues to cache")

            return issues

        except Exception as e:
            logger.error(f"Failed to collect issues: {e}")
            raise

    def _build_default_jql(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None
    ) -> str:
        """Build default JQL query"""
        conditions = []

        if project:
            conditions.append(f"project = {project}")

        if status:
            conditions.append(f"status = '{status}'")
        else:
            # Default: closed/resolved issues in last 180 days
            conditions.append("status IN (Done, Resolved, Closed)")
            conditions.append("resolved >= -180d")

        if conditions:
            return " AND ".join(conditions) + " ORDER BY updated DESC"
        else:
            return "ORDER BY updated DESC"

    def get_issue_details(self, issue_key: str) -> Optional[JiraIssue]:
        """
        Get detailed information for a specific issue

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            JiraIssue object or None
        """
        try:
            issue = self.mcp_client.get_jira_issue(issue_key)

            if issue:
                # Save to cache
                self.save_to_cache([issue])
                logger.info(f"Retrieved and cached issue: {issue_key}")

            return issue

        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return None

    def save_to_cache(self, issues: List[JiraIssue]) -> int:
        """
        Save issues to SQLite cache with batch processing

        Args:
            issues: List of JiraIssue objects

        Returns:
            Number of issues saved
        """
        if not issues:
            return 0

        saved_count = 0
        total_batches = (len(issues) + self.batch_size - 1) // self.batch_size

        logger.info(f"Saving {len(issues)} issues in {total_batches} batches")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Process in batches with progress bar
                for i in tqdm(range(0, len(issues), self.batch_size),
                             desc="Saving to cache",
                             total=total_batches):
                    batch = issues[i:i + self.batch_size]

                    for issue in batch:
                        try:
                            self._save_single_issue(conn, issue)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"Failed to save issue {issue.key}: {e}")
                            # Continue processing other issues

                conn.commit()

        except Exception as e:
            logger.error(f"Database error during save: {e}")
            raise

        return saved_count

    def _save_single_issue(self, conn: sqlite3.Connection, issue: JiraIssue):
        """Save a single issue to database"""
        # Convert lists to JSON strings
        labels_json = json.dumps(issue.labels) if issue.labels else "[]"
        components_json = json.dumps(issue.components) if issue.components else "[]"
        raw_data_json = issue.model_dump_json()

        conn.execute("""
            INSERT OR REPLACE INTO jira_issues (
                issue_key, summary, description, status, issue_type, priority,
                assignee, reporter, created_at, updated_at, resolved_at,
                labels, components, raw_data, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            issue.key,
            issue.summary,
            issue.description,
            issue.status,
            issue.issue_type,
            issue.priority,
            issue.assignee,
            issue.reporter,
            issue.created,
            issue.updated,
            None,  # resolved_at - not in current model
            labels_json,
            components_json,
            raw_data_json,
        ))

    def incremental_update(self, since_hours: int = 24) -> List[JiraIssue]:
        """
        Perform incremental update - fetch only recently updated issues

        Args:
            since_hours: Fetch issues updated in last N hours

        Returns:
            List of updated issues
        """
        logger.info(f"Starting incremental update (last {since_hours} hours)")

        # Build JQL for recent updates
        jql = f"updated >= -{since_hours}h ORDER BY updated DESC"

        try:
            issues = self.collect_issues(jql=jql, max_results=1000)
            logger.info(f"Incremental update completed: {len(issues)} issues")
            return issues

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            raise

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync time from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT MAX(last_synced_at) FROM jira_issues
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    return datetime.fromisoformat(result[0])

        except Exception as e:
            logger.error(f"Failed to get last sync time: {e}")

        return None

    def get_cached_issues(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve cached issues from database

        Args:
            status: Filter by status
            limit: Maximum results

        Returns:
            List of issue dictionaries
        """
        query = "SELECT * FROM jira_issues"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve cached issues: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        stats = {
            "total_issues": 0,
            "last_sync": None,
            "status_distribution": {},
            "date_range": {"oldest": None, "newest": None}
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total count
                cursor = conn.execute("SELECT COUNT(*) FROM jira_issues")
                stats["total_issues"] = cursor.fetchone()[0]

                # Last sync
                cursor = conn.execute("SELECT MAX(last_synced_at) FROM jira_issues")
                result = cursor.fetchone()
                if result[0]:
                    stats["last_sync"] = result[0]

                # Status distribution
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM jira_issues
                    GROUP BY status
                    ORDER BY count DESC
                """)
                stats["status_distribution"] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }

                # Date range
                cursor = conn.execute("""
                    SELECT MIN(created_at), MAX(updated_at)
                    FROM jira_issues
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
                conn.execute("DELETE FROM jira_comments")
                conn.execute("DELETE FROM jira_issues")
                conn.commit()
            logger.info("Cache cleared successfully")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise
