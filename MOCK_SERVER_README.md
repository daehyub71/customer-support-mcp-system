# Mock MCP Server for Testing

## Problem Statement

The Atlassian MCP server (mcp-atlassian) requires Atlassian Cloud credentials (email + API token) to authenticate and register tools. However, we are using a **self-hosted Confluence server** which has different authentication requirements.

### Issue Details

The MCP server logs show:
```
DEBUG - Excluding Jira tool 'jira_search' as Jira configuration/authentication is incomplete.
DEBUG - Excluding Confluence tool 'confluence_search' as Confluence configuration/authentication is incomplete.
DEBUG - No Authorization header provided for /mcp. Will proceed with global/fallback server configuration if applicable.
```

Even with valid Atlassian Cloud API tokens in the environment, the MCP server cannot connect to the local Confluence instance because:
1. Local Confluence doesn't use Cloud API token authentication
2. Local Confluence may require setup/configuration first
3. MCP server is designed primarily for Atlassian Cloud

## Solution: Mock MCP Server

To unblock development and testing, we've created a **mock MCP server** that simulates the Atlassian MCP protocol and responses.

### Features

✅ Implements MCP Protocol (2024-11-05)
✅ Supports SSE (Server-Sent Events) response format
✅ Provides mock Jira and Confluence tools
✅ Generates realistic test data
✅ Session management with session IDs

### Supported Tools

**Jira Tools:**
- `jira_search` - Search Jira issues using JQL
- `jira_get_issue` - Get details of a specific issue

**Confluence Tools:**
- `confluence_search` - Search Confluence pages
- `confluence_get_page` - Get page details

### Mock Data Characteristics

**Jira Issues:**
- 180-day date range
- Multiple statuses (Done, Resolved)
- Realistic field structure
- Labels and metadata

**Confluence Pages:**
- 365-day date range
- HTML content (storage and view formats)
- Space organization
- Version history

## Usage

### 1. Start the Mock Server

```bash
# Terminal 1: Start mock MCP server on port 9001
python scripts/mock_mcp_server.py
```

Output:
```
Starting Mock MCP Server on http://localhost:9001/mcp/
This server simulates Atlassian MCP responses for testing
```

### 2. Test with Mock Server

```bash
# Terminal 2: Run tests with mock server
python scripts/test_with_mock.py
```

### 3. Update Configuration

To use the mock server in your code, update the MCP client initialization:

```python
# Use mock server (port 9001)
client = MCPClient(host="localhost", port=9001, timeout=30)

# Or use real MCP server (port 9000) when available
client = MCPClient(host="localhost", port=9000, timeout=30)
```

### 4. Environment Variables

For mock server (temporary testing):
```bash
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=9001  # Mock server port
```

For real MCP server (when authentication is fixed):
```bash
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=9000  # Real MCP server port
```

## Testing Workflow

### Test Jira Collection

```bash
# Start mock server
python scripts/mock_mcp_server.py

# In another terminal, test Jira collection
python scripts/test_with_mock.py
```

Expected output:
```
Testing Jira Collection with Mock Server
1. Connecting to mock MCP server...
   [OK] Connected
2. Listing available tools...
   [OK] Found 4 tools
3. Creating Jira collector...
   [OK] Collector created
4. Collecting Jira issues...
   [OK] Collected 20 issues
   [OK] Saved to database
5. Sample issue:
   Key: MOCK-1000
   Summary: Mock Issue 1: Customer support request
   Status: Done
[SUCCESS] Jira collection test completed
```

### Test Confluence Collection

Same process, but testing Confluence pages:
```
Testing Confluence Collection with Mock Server
...
[SUCCESS] Confluence collection test completed
```

## Integration with Existing Code

The mock server is **fully compatible** with the existing MCP client and collectors:

```python
from app.mcp.mcp_client import MCPClient
from app.mcp.jira_collector import JiraCollector
from app.mcp.confluence_collector import ConfluenceCollector

# Just change the port to 9001
client = MCPClient(host="localhost", port=9001)
client.connect()

# Everything else works the same
jira_collector = JiraCollector(client)
issues = jira_collector.collect_issues(jql="...", max_results=50)
```

## Transitioning to Real MCP Server

When the real MCP server authentication is resolved:

1. **Option 1: Atlassian Cloud Setup**
   - Create Atlassian Cloud account
   - Generate API token
   - Update docker-compose.yml with Cloud URL and credentials
   - Change port from 9001 to 9000

2. **Option 2: Local Confluence API**
   - Complete Confluence setup wizard
   - Create API token or use basic auth
   - Configure MCP server for local authentication
   - Change port from 9001 to 9000

3. **No Code Changes Required**
   - Just update environment variables
   - MCP client works with both mock and real servers

## File Structure

```
customer-support-mcp-system/
├── scripts/
│   ├── mock_mcp_server.py      # Mock MCP server implementation
│   └── test_with_mock.py       # Test script for mock server
├── app/
│   ├── mcp/
│   │   ├── mcp_client.py       # MCP client (works with both)
│   │   ├── jira_collector.py   # Jira collector
│   │   └── confluence_collector.py  # Confluence collector
│   └── data/
│       └── cache/              # Test databases created here
└── MOCK_SERVER_README.md       # This file
```

## Current Status

✅ **Completed:**
- MCP Client implementation with SSE support
- Jira Collector with SQLite caching
- Confluence Collector with HTML cleanup
- Mock MCP server for testing
- Unit tests (16 tests passing)

❌ **Blocked (Real MCP Server):**
- Atlassian Cloud authentication
- Local Confluence API integration

✅ **Workaround (Mock Server):**
- Full testing capability
- Development can continue
- Data collection pipeline validated

## Next Steps

With the mock server, you can now:

1. ✅ Test the complete data collection pipeline
2. ✅ Proceed to Task 2.1: RAG System implementation
3. ✅ Develop and test LangGraph workflows
4. ✅ Build the complete system with mock data

Later, when MCP server authentication is resolved:
5. ⏳ Switch to real MCP server (just change port)
6. ⏳ Collect real Jira/Confluence data
7. ⏳ Deploy to production

## Commands Reference

```bash
# Start mock server
python scripts/mock_mcp_server.py

# Test with mock server
python scripts/test_with_mock.py

# Test MCP connection
python scripts/test_mcp_connection.py

# Collect data with mock server (update port to 9001 in .env first)
python scripts/collect_data.py --source jira --limit 50
python scripts/collect_data.py --source confluence --spaces MOCK --limit 25
```
