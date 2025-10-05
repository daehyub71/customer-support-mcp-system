"""
MCP (Model Context Protocol) Client Module

Atlassian MCP Server communication client module
"""
from .mcp_client import MCPClient
from .jira_collector import JiraCollector
from .confluence_collector import ConfluenceCollector
from .types import (
    Tool,
    Resource,
    ToolCallRequest,
    ToolCallResponse,
    JiraIssue,
    ConfluencePage,
    SearchResult,
)

__all__ = [
    "MCPClient",
    "JiraCollector",
    "ConfluenceCollector",
    "Tool",
    "Resource",
    "ToolCallRequest",
    "ToolCallResponse",
    "JiraIssue",
    "ConfluencePage",
    "SearchResult",
]
