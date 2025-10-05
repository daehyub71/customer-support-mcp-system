-- Jira Issues Cache Schema
-- Stores collected Jira issues and comments from MCP Server

-- Main Issues Table
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
    labels TEXT,  -- JSON array as text
    components TEXT,  -- JSON array as text
    raw_data TEXT,  -- Full JSON response
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_jira_updated_at ON jira_issues(updated_at);
CREATE INDEX IF NOT EXISTS idx_jira_status ON jira_issues(status);
CREATE INDEX IF NOT EXISTS idx_jira_collected_at ON jira_issues(collected_at);
CREATE INDEX IF NOT EXISTS idx_jira_assignee ON jira_issues(assignee);

-- Jira Comments Table
CREATE TABLE IF NOT EXISTS jira_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_key TEXT NOT NULL,
    comment_id TEXT UNIQUE,
    author TEXT,
    body TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_key) REFERENCES jira_issues(issue_key) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_issue_key ON jira_comments(issue_key);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON jira_comments(created_at);

-- Collection Metadata Table
CREATE TABLE IF NOT EXISTS collection_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,  -- 'jira' or 'confluence'
    collection_type TEXT,  -- 'full', 'incremental'
    jql_query TEXT,
    total_collected INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    started_at DATETIME,
    completed_at DATETIME,
    status TEXT,  -- 'running', 'completed', 'failed'
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_metadata_source ON collection_metadata(source);
CREATE INDEX IF NOT EXISTS idx_metadata_started ON collection_metadata(started_at);

-- Confluence Pages Cache
CREATE TABLE IF NOT EXISTS confluence_pages (
    page_id TEXT PRIMARY KEY,
    space_key TEXT NOT NULL,
    space_name TEXT,
    title TEXT NOT NULL,
    body_storage TEXT,      -- HTML original content
    body_view TEXT,         -- Rendered HTML view
    body_cleaned TEXT,      -- Cleaned text for search
    version INTEGER,
    creator TEXT,
    last_modifier TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    labels TEXT,            -- JSON array as text
    url TEXT,
    parent_id TEXT,
    raw_data TEXT,          -- Full JSON response
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_confluence_space_key ON confluence_pages(space_key);
CREATE INDEX IF NOT EXISTS idx_confluence_updated_at ON confluence_pages(updated_at);
CREATE INDEX IF NOT EXISTS idx_confluence_collected_at ON confluence_pages(collected_at);
CREATE INDEX IF NOT EXISTS idx_confluence_title ON confluence_pages(title);

-- Confluence Spaces Table
CREATE TABLE IF NOT EXISTS confluence_spaces (
    space_key TEXT PRIMARY KEY,
    space_name TEXT NOT NULL,
    space_type TEXT,        -- 'global' or 'personal'
    description TEXT,
    homepage_id TEXT,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spaces_collected_at ON confluence_spaces(collected_at);
