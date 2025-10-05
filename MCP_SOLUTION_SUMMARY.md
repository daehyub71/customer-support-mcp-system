# MCP Server Authentication Issue & Mock Server Solution

## Problem Summary

The real Atlassian MCP server (port 9000) cannot authenticate with the local Confluence instance because:

1. **MCP Server Design**: The `mcp-atlassian` Docker image is designed for **Atlassian Cloud** (cloud.atlassian.com) which uses:
   - Email + API Token authentication
   - Cloud-specific API endpoints

2. **Our Setup**: We have a **self-hosted Confluence server** (localhost:8090) which:
   - Has different authentication mechanisms
   - Requires initial setup/configuration
   - Doesn't use Cloud API tokens

3. **Server Logs Show**:
   ```
   DEBUG - Excluding Jira tool 'jira_search' as Jira configuration/authentication is incomplete.
   DEBUG - Excluding Confluence tool 'confluence_search' as Confluence configuration/authentication is incomplete.
   ```

## Solution: Mock MCP Server

We've implemented a **pure Python mock MCP server** (`scripts/mock_mcp_server.py`) that:

✅ Implements MCP Protocol 2024-11-05
✅ Provides SSE (Server-Sent Events) responses
✅ Simulates 4 Atlassian tools (Jira search/get, Confluence search/get)
✅ Generates realistic test data
✅ **No external dependencies** - uses only Python standard library
✅ Runs on port 9001

## Test Results

```
C:\data_analysis\customer-support-mcp-system>python scripts\quick_test_mock.py

Connecting to mock MCP server...
[OK] Connected

Listing tools...
[OK] Found 4 tools:
  - jira_search: Search Jira issues using JQL
  - jira_get_issue: Get details of a specific Jira issue
  - confluence_search: Search Confluence pages
  - confluence_get_page: Get details of a specific Confluence page

Calling jira_search...
[OK] Found 5 issues
  Sample: MOCK-1000 - Mock Issue 1: Customer support request

[SUCCESS] Mock server test completed!
```

## Mock Server Features

### Supported Tools

1. **jira_search**
   - Accepts: `jql` (string), `max_results` (int)
   - Returns: Realistic Jira issues with all required fields
   - Date range: Last 180 days
   - Statuses: Done, Resolved

2. **jira_get_issue**
   - Accepts: `issue_key` (string)
   - Returns: Detailed issue with metadata

3. **confluence_search**
   - Accepts: `cql` (string), `limit` (int)
   - Returns: Pages with HTML content (storage + view formats)
   - Date range: Last 365 days

4. **confluence_get_page**
   - Accepts: `page_id` (string)
   - Returns: Full page with rich HTML content

### Mock Data Characteristics

**Jira Issues:**
- Keys: MOCK-1000, MOCK-1001, ...
- Realistic field structure (summary, description, status, dates, assignee, reporter, priority, labels)
- Proper timestamp progression
- Mix of Done/Resolved statuses

**Confluence Pages:**
- IDs: mock-page-1, mock-page-2, ...
- HTML content with formatting
- Space: MOCK
- Version tracking
- Web links

## Usage Instructions

### 1. Start Mock Server

```bash
# In Terminal 1
cd customer-support-mcp-system
python scripts/mock_mcp_server.py
```

Output:
```
================================================================================
Mock MCP Server Starting
================================================================================
Server running on http://localhost:9001/mcp/
This server simulates Atlassian MCP responses for testing
Press Ctrl+C to stop
================================================================================
```

### 2. Update Environment (Optional)

To permanently use mock server, update `.env`:

```bash
MCP_SERVER_PORT=9001  # Change from 9000 to 9001
```

### 3. Use with Existing Code

The mock server is **fully compatible** with existing MCP client:

```python
from app.mcp.mcp_client import MCPClient
from app.mcp.jira_collector import JiraCollector

# Just point to port 9001
client = MCPClient(host="localhost", port=9001)
client.connect()

# Everything else works the same
collector = JiraCollector(client)
issues = collector.collect_issues(jql="...", max_results=50)
```

### 4. Run Quick Test

```bash
python scripts/quick_test_mock.py
```

### 5. Run Full Data Collection Test

```bash
python scripts/test_with_mock.py
```

## Current Project Status

### ✅ Completed (Tasks 1.2 - 1.4)

1. **MCP Client Module** (`app/mcp/mcp_client.py`)
   - Full MCP Protocol 2024-11-05 implementation
   - SSE response parsing
   - Session management
   - Exponential backoff retry (1s, 2s, 4s)
   - 16 unit tests passing

2. **Jira Data Collector** (`app/mcp/jira_collector.py`)
   - SQLite caching with schema
   - Batch processing (50 items/batch)
   - Progress bars with tqdm
   - Incremental updates
   - Unit tests

3. **Confluence Data Collector** (`app/mcp/confluence_collector.py`)
   - SQLite caching
   - HTML cleanup with BeautifulSoup4
   - Space/page listing
   - Batch processing
   - Unit tests

4. **Mock MCP Server** (`scripts/mock_mcp_server.py`)
   - Pure Python implementation
   - 4 tool implementations
   - Realistic mock data generation
   - SSE protocol support

5. **Test Infrastructure**
   - `scripts/test_mcp_connection.py` - Connection diagnostics
   - `scripts/quick_test_mock.py` - Quick validation
   - `scripts/test_with_mock.py` - Full collector tests
   - `scripts/collect_data.py` - CLI interface

### 📁 File Structure

```
customer-support-mcp-system/
├── app/
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── types.py                    # Pydantic models
│   │   ├── mcp_client.py               # MCP client with SSE support
│   │   ├── jira_collector.py           # Jira data collector
│   │   └── confluence_collector.py     # Confluence data collector
│   ├── utils/
│   │   └── config.py                   # Environment config
│   └── data/
│       └── cache/
│           └── schema.sql              # SQLite schema
├── scripts/
│   ├── mock_mcp_server.py             # Mock server (NO DEPENDENCIES!)
│   ├── quick_test_mock.py             # Quick test
│   ├── test_with_mock.py              # Full test suite
│   ├── test_mcp_connection.py         # Connection diagnostics
│   └── collect_data.py                # CLI data collection
├── tests/
│   ├── test_mcp_client.py             # 16 tests
│   ├── test_jira_collector.py
│   └── test_confluence_collector.py
├── .env                                # Environment config
├── requirements.txt
├── MOCK_SERVER_README.md              # Mock server documentation
└── MCP_SOLUTION_SUMMARY.md            # This file
```

## Next Steps

### Option 1: Continue with Mock Server (Recommended)

✅ Proceed to **Task 2.1: RAG System Implementation**
- Use mock data for development
- No blocking issues
- Full testing capability
- Later: swap to real MCP server by changing port

### Option 2: Fix Real MCP Server (If needed for production)

Two approaches:

**A. Use Atlassian Cloud:**
1. Create Atlassian Cloud account
2. Set up Jira/Confluence Cloud instances
3. Generate Cloud API token
4. Update `.env` with Cloud URL and credentials
5. Restart mcp-atlassian container

**B. Configure Local Confluence:**
1. Complete Confluence setup wizard (http://localhost:8090)
2. Research mcp-atlassian local auth support
3. May require custom MCP server configuration or alternative MCP server

## Commands Reference

```bash
# Start Mock Server (Terminal 1)
python scripts/mock_mcp_server.py

# Quick Test (Terminal 2)
python scripts/quick_test_mock.py

# Full Test Suite
python scripts/test_with_mock.py

# Run Unit Tests
pytest tests/ -v

# Check Real MCP Server (Debugging)
python scripts/test_mcp_connection.py

# Collect Data with Mock Server
python scripts/collect_data.py --source jira --limit 50
python scripts/collect_data.py --source confluence --spaces MOCK --limit 25
```

## Key Achievements

1. ✅ **Complete MCP Protocol Implementation** - Handles SSE, session management, retries
2. ✅ **Robust Data Collectors** - SQLite caching, batch processing, error handling
3. ✅ **Mock Server Workaround** - Zero external dependencies, fully functional
4. ✅ **Comprehensive Testing** - Unit tests, integration tests, diagnostic tools
5. ✅ **Development Unblocked** - Can proceed to RAG system without waiting for MCP auth fix

## Recommendation

**Proceed with mock server for Tasks 2.x (RAG System):**
- Mock data is realistic and sufficient for development
- No dependencies on external services
- Easy to switch to real MCP server later (just change port)
- Maintains development velocity

The MCP client, collectors, and RAG system will work identically with both mock and real servers. The only difference is the data source (mock vs. real Atlassian).
