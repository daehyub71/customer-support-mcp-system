"""
Mock MCP Server for Testing (Pure Python - No Dependencies)

Simulates Atlassian MCP server responses for Jira and Confluence tools
when the actual MCP server is not available or not properly configured.
"""
import json
import uuid
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP protocol"""

    # Session storage (shared across requests)
    sessions: Dict[str, Dict[str, Any]] = {}

    def do_POST(self):
        """Handle POST requests"""
        # Only handle /mcp/ endpoint
        if not self.path.startswith('/mcp'):
            self.send_error(404, "Not Found")
            return

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length)

        try:
            body = json.loads(body_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Get or create session
        session_id = self.headers.get('mcp-session-id')
        if not session_id:
            session_id = str(uuid.uuid4()).replace("-", "")
            self.sessions[session_id] = {"initialized": False}

        # Process MCP request
        method = body.get("method")
        request_id = body.get("id")
        params = body.get("params", {})

        # Route to appropriate handler
        if method == "initialize":
            response_data = self.handle_initialize(request_id, params, session_id)
        elif method == "notifications/initialized":
            response_data = {"jsonrpc": "2.0", "id": request_id, "result": {}}
        elif method == "tools/list":
            response_data = self.handle_tools_list(request_id)
        elif method == "tools/call":
            response_data = self.handle_tool_call(request_id, params)
        elif method == "resources/list":
            response_data = {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
        else:
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        # Send SSE response
        self.send_sse_response(response_data, session_id)

    def handle_initialize(self, request_id: str, params: Dict, session_id: str) -> Dict[str, Any]:
        """Handle initialize request"""
        self.sessions[session_id]["initialized"] = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "experimental": {},
                    "prompts": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "Mock Atlassian MCP",
                    "version": "1.0.0-mock"
                }
            }
        }

    def handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "jira_search",
                        "description": "Search Jira issues using JQL",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "jql": {"type": "string"},
                                "max_results": {"type": "integer", "default": 50}
                            }
                        }
                    },
                    {
                        "name": "jira_get_issue",
                        "description": "Get details of a specific Jira issue",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "issue_key": {"type": "string"}
                            },
                            "required": ["issue_key"]
                        }
                    },
                    {
                        "name": "confluence_search",
                        "description": "Search Confluence pages",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "cql": {"type": "string"},
                                "limit": {"type": "integer", "default": 25}
                            }
                        }
                    },
                    {
                        "name": "confluence_get_page",
                        "description": "Get details of a specific Confluence page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "page_id": {"type": "string"}
                            },
                            "required": ["page_id"]
                        }
                    }
                ]
            }
        }

    def handle_tool_call(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "jira_search":
            mock_data = self.generate_mock_jira_issues(tool_args.get("maxResults", 10))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(mock_data, indent=2)}]
                }
            }

        elif tool_name == "jira_get_issue":
            mock_data = self.generate_mock_jira_issue(tool_args.get("issue_key"))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(mock_data, indent=2)}]
                }
            }

        elif tool_name == "confluence_search":
            mock_data = self.generate_mock_confluence_pages(tool_args.get("limit", 10))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(mock_data, indent=2)}]
                }
            }

        elif tool_name == "confluence_get_page":
            mock_data = self.generate_mock_confluence_page(tool_args.get("page_id"))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(mock_data, indent=2)}]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

    def send_sse_response(self, data: Dict[str, Any], session_id: str):
        """Send Server-Sent Events formatted response"""
        json_str = json.dumps(data)
        sse_data = f"event: message\ndata: {json_str}\n\n"
        sse_bytes = sse_data.encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('mcp-session-id', session_id)
        self.send_header('Content-Length', str(len(sse_bytes)))
        self.send_header('Connection', 'close')
        self.end_headers()

        self.wfile.write(sse_bytes)
        self.wfile.flush()

    def generate_mock_jira_issues(self, count: int = 10) -> Dict[str, Any]:
        """Generate mock Jira search results"""
        issues = []
        base_date = datetime.now() - timedelta(days=180)

        for i in range(count):
            issue_date = base_date + timedelta(days=i*5)
            # Flatten structure to match JiraIssue model
            issues.append({
                "key": f"MOCK-{1000 + i}",
                "summary": f"Mock Issue {i+1}: Customer support request",
                "description": f"This is a mock issue for testing purposes. Issue #{i+1}",
                "status": "Done" if i % 3 == 0 else "Resolved",
                "created": issue_date.isoformat(),
                "updated": (issue_date + timedelta(days=2)).isoformat(),
                "assignee": f"User {i % 5 + 1}",
                "reporter": "Mock Reporter",
                "priority": "Medium",
                "labels": ["support", "mock-data"]
            })

        return {"total": count, "issues": issues}

    def generate_mock_jira_issue(self, issue_key: str) -> Dict[str, Any]:
        """Generate a single mock Jira issue"""
        return {
            "key": issue_key,
            "summary": f"Mock issue: {issue_key}",
            "description": "This is a detailed mock issue description for testing.",
            "status": "Done",
            "created": (datetime.now() - timedelta(days=30)).isoformat(),
            "updated": (datetime.now() - timedelta(days=5)).isoformat(),
            "assignee": "Mock User",
            "reporter": "Mock Reporter",
            "priority": "High",
            "labels": ["support", "urgent", "mock-data"]
        }

    def generate_mock_confluence_pages(self, count: int = 10) -> Dict[str, Any]:
        """Generate mock Confluence search results"""
        pages = []
        base_date = datetime.now() - timedelta(days=365)

        for i in range(count):
            page_date = base_date + timedelta(days=i*10)
            pages.append({
                "id": f"mock-page-{i+1}",
                "type": "page",
                "status": "current",
                "title": f"Mock Documentation Page {i+1}",
                "space": "MOCK",  # Simplified to match ConfluencePage model
                "content": f"<p>This is mock page content for page {i+1}. Contains important information.</p>",
                "version": i % 5 + 1,
                "created": page_date.isoformat(),
                "updated": (page_date + timedelta(days=5)).isoformat(),
                "author": "Mock Author",
                "labels": ["documentation", "mock-data"],
                # Keep original structure for compatibility
                "_original": {
                    "space": {"key": "MOCK", "name": "Mock Space"},
                    "version": {"number": i % 5 + 1},
                    "body": {
                        "storage": {
                            "value": f"<p>This is mock page content for page {i+1}. Contains important information.</p>",
                            "representation": "storage"
                        },
                        "view": {
                            "value": f"<p>This is mock page content for page {i+1}. Contains important information.</p>",
                            "representation": "view"
                        }
                    },
                    "_links": {
                        "webui": f"/pages/viewpage.action?pageId=mock-page-{i+1}",
                        "self": f"https://mock.atlassian.net/wiki/rest/api/content/mock-page-{i+1}"
                    }
                }
            })

        return {"results": pages, "size": count}

    def generate_mock_confluence_page(self, page_id: str) -> Dict[str, Any]:
        """Generate a single mock Confluence page"""
        return {
            "id": page_id,
            "type": "page",
            "status": "current",
            "title": f"Mock Page: {page_id}",
            "space": "MOCK",
            "content": "<p>This is detailed mock page content with <strong>rich formatting</strong>.</p><ul><li>Item 1</li><li>Item 2</li></ul>",
            "version": 3,
            "created": (datetime.now() - timedelta(days=60)).isoformat(),
            "updated": (datetime.now() - timedelta(days=10)).isoformat(),
            "author": "Mock Author",
            "labels": ["important", "documentation"]
        }

    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host='localhost', port=9001):
    """Run the mock MCP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, MCPHandler)

    print("=" * 80)
    print(f"Mock MCP Server Starting")
    print("=" * 80)
    print(f"Server running on http://{host}:{port}/mcp/")
    print("This server simulates Atlassian MCP responses for testing")
    print("Press Ctrl+C to stop")
    print("=" * 80)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()
        print("Server stopped")


if __name__ == "__main__":
    run_server()
