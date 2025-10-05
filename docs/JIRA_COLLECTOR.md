# Jira Data Collector Documentation

## Overview

Jira Collector는 MCP Server를 통해 Jira 이슈를 수집하고 SQLite 캐시에 저장하는 모듈입니다.

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  collect_data   │─────▶│  JiraCollector  │─────▶│  MCP Client     │
│    (script)     │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                  │                         │
                                  ▼                         ▼
                         ┌─────────────────┐      ┌─────────────────┐
                         │  SQLite Cache   │      │   MCP Server    │
                         │  (jira_cache.db)│      │  (Atlassian)    │
                         └─────────────────┘      └─────────────────┘
```

## Components

### 1. JiraCollector Class

**Location**: `app/mcp/jira_collector.py`

**Key Methods**:

- `collect_issues(jql, max_results)` - JQL 기반 이슈 수집
- `get_issue_details(issue_key)` - 단일 이슈 상세 조회
- `save_to_cache(issues)` - SQLite 저장 (50건씩 배치)
- `incremental_update(since_hours)` - 증분 업데이트
- `get_collection_stats()` - 수집 통계 조회
- `clear_cache()` - 캐시 초기화

**Features**:

- ✅ 배치 처리 (50건씩)
- ✅ Progress bar (tqdm)
- ✅ 에러 핸들링 (개별 실패 시 계속 진행)
- ✅ UPSERT 로직 (중복 방지)
- ✅ 증분 업데이트

### 2. SQLite Schema

**Location**: `app/data/cache/schema.sql`

**Tables**:

- `jira_issues` - 이슈 데이터
- `jira_comments` - 이슈 코멘트
- `collection_metadata` - 수집 메타데이터
- `confluence_pages` - Confluence 페이지 (향후 사용)

**Indexes**:
- `idx_jira_updated_at` - updated_at 기준 정렬
- `idx_jira_status` - status 필터링
- `idx_jira_collected_at` - 수집 시간 기준
- `idx_jira_assignee` - 담당자 필터링

### 3. Collection Script

**Location**: `scripts/collect_data.py`

**Usage**:

```bash
# 기본 수집 (최근 180일 완료된 이슈)
python scripts/collect_data.py --source jira

# 커스텀 JQL
python scripts/collect_data.py --source jira --jql "project = MYPROJ AND status = Done"

# 특정 프로젝트
python scripts/collect_data.py --source jira --project PROJ --limit 500

# 증분 업데이트 (최근 24시간)
python scripts/collect_data.py --source jira --incremental 24

# 통계 확인
python scripts/collect_data.py --stats

# 캐시 초기화
python scripts/collect_data.py --clear-cache --force
```

**Arguments**:

| Argument | Description | Default |
|----------|-------------|---------|
| `--source` | Data source (jira/confluence) | Required |
| `--jql` | JQL query string | `status IN (Done, Resolved, Closed) AND resolved >= -180d` |
| `--project` | Project key filter | None |
| `--status` | Status filter | None |
| `--limit` | Max results | 1000 |
| `--incremental` | Hours for incremental update | None |
| `--stats` | Show statistics | False |
| `--clear-cache` | Clear cache | False |
| `--mcp-host` | MCP server host | localhost |
| `--mcp-port` | MCP server port | 9000 |
| `--verbose` | Verbose output | False |

## Data Flow

### Full Collection

```
1. User runs: python scripts/collect_data.py --source jira --jql "..."
2. Script connects to MCP Server
3. JiraCollector.collect_issues() called
   ├─ MCPClient.search_jira_issues() - Fetch from MCP
   ├─ JiraCollector.save_to_cache() - Save to SQLite
   │  ├─ Split into batches (50 issues/batch)
   │  ├─ Show progress bar
   │  └─ UPSERT each issue
   └─ Return collected issues
4. Display statistics
5. Disconnect from MCP Server
```

### Incremental Update

```
1. User runs: python scripts/collect_data.py --source jira --incremental 24
2. JiraCollector.incremental_update(24) called
3. Build JQL: "updated >= -24h ORDER BY updated DESC"
4. Collect and save issues (same as full collection)
5. Only recently updated issues are fetched
```

## Database Schema

### jira_issues Table

```sql
CREATE TABLE jira_issues (
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
    labels TEXT,           -- JSON array
    components TEXT,       -- JSON array
    raw_data TEXT,         -- Full JSON
    collected_at DATETIME,
    last_synced_at DATETIME
);
```

### Query Examples

```sql
-- Get all Done issues
SELECT * FROM jira_issues WHERE status = 'Done';

-- Get recent issues
SELECT * FROM jira_issues ORDER BY updated_at DESC LIMIT 10;

-- Status distribution
SELECT status, COUNT(*) FROM jira_issues GROUP BY status;

-- Issues by assignee
SELECT assignee, COUNT(*) FROM jira_issues GROUP BY assignee;
```

## Error Handling

### Collection Errors

- **MCP Connection Failed**: Retries 3 times with exponential backoff (1s, 2s, 4s)
- **Individual Issue Save Failed**: Logged but continues with next issue
- **Database Error**: Transaction rolled back, exception raised

### Logging

Logs are written to:
- Console (stdout)
- File: `app/logs/collection.log`

Log levels:
- `INFO` - Normal operations
- `WARNING` - Non-critical issues
- `ERROR` - Failures with stack trace
- `DEBUG` - Verbose mode (--verbose flag)

## Performance

### Batch Processing

Issues are saved in batches of 50 to optimize database performance:

```python
batch_size = 50
for i in range(0, len(issues), batch_size):
    batch = issues[i:i + batch_size]
    # Process batch
```

### Progress Tracking

Uses `tqdm` for progress bars:

```
Saving to cache: 100%|████████████| 20/20 [00:05<00:00,  3.85it/s]
```

### Expected Performance

- 1000 issues: ~30-60 seconds (depends on MCP server)
- Database write: ~50 issues/second
- Network: Depends on MCP server response time

## Testing

### Unit Tests

**Location**: `tests/test_jira_collector.py`

**Coverage**:

- ✅ Database initialization
- ✅ Issue collection
- ✅ SQLite caching (save/retrieve)
- ✅ Batch processing
- ✅ UPSERT logic
- ✅ Incremental updates
- ✅ Statistics queries
- ✅ Error handling

**Run Tests**:

```bash
# All tests
pytest tests/test_jira_collector.py -v

# Specific test class
pytest tests/test_jira_collector.py::TestJiraCollectorCaching -v

# With coverage
pytest tests/test_jira_collector.py --cov=app.mcp.jira_collector
```

## Examples

### Example 1: First-time Collection

```bash
# Collect last 180 days of completed issues
python scripts/collect_data.py --source jira

# Output:
# ================================================================================
# Starting Jira Data Collection
# ================================================================================
# Connecting to MCP Server...
# MCP connection established successfully
#
# Current cache statistics:
#   Total issues: 0
#   Last sync: None
#
# Collecting issues with JQL: status IN (Done, Resolved, Closed) AND resolved >= -180d
# Saving to cache: 100%|████████████| 20/20 [00:05<00:00,  3.85it/s]
#
# ================================================================================
# Collection completed successfully!
# Issues collected: 523
# ================================================================================
```

### Example 2: Incremental Update

```bash
# Update issues changed in last 6 hours
python scripts/collect_data.py --source jira --incremental 6

# Runs every 6 hours via cron:
# 0 */6 * * * cd /path/to/project && python scripts/collect_data.py --source jira --incremental 6
```

### Example 3: Check Statistics

```bash
python scripts/collect_data.py --stats

# Output:
# Cache Statistics
# ================================================================================
# Jira Issues Cache: app/data/cache/jira_cache.db
#   Total issues: 523
#   Last sync: 2024-10-04 14:30:15
#   Date range: 2024-04-07 to 2024-10-04
#
#   Status distribution:
#     Done: 312
#     Resolved: 156
#     Closed: 55
```

## Troubleshooting

### Issue: MCP Connection Failed

```
ERROR - Failed to connect to MCP server: Connection refused
```

**Solution**:
1. Check MCP server is running
2. Verify `MCP_SERVER_HOST` and `MCP_SERVER_PORT` in `.env`
3. Test connection: `curl http://localhost:9000/mcp`

### Issue: No Issues Collected

```
Issues collected: 0
```

**Solution**:
1. Check JQL query is valid
2. Verify date range (default: last 180 days)
3. Test MCP server directly with same JQL

### Issue: Database Locked

```
ERROR - Database error: database is locked
```

**Solution**:
1. Close other processes using the database
2. Check for stale locks: `lsof app/data/cache/jira_cache.db`
3. Wait and retry

## Future Enhancements

- [ ] Confluence page collection
- [ ] Issue comments collection
- [ ] Attachment download
- [ ] Custom field mapping
- [ ] Parallel batch processing
- [ ] Real-time webhooks
- [ ] Elasticsearch integration
