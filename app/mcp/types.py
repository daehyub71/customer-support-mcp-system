"""
MCP Protocol Data Types

MCP(Model Context Protocol) 통신에 사용되는 데이터 타입 정의
"""
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ToolParameter(BaseModel):
    """Tool 파라미터 정의"""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


class Tool(BaseModel):
    """MCP Tool 정의"""
    name: str
    description: str
    parameters: List[ToolParameter]


class ResourceContent(BaseModel):
    """리소스 컨텐츠"""
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None


class Resource(BaseModel):
    """MCP Resource 정의"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class MCPRequest(BaseModel):
    """MCP 요청 메시지"""
    model_config = {"extra": "allow"}  # Allow extra fields

    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP 응답 메시지"""
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP 에러"""
    code: int
    message: str
    data: Optional[Any] = None


class ToolCallRequest(BaseModel):
    """Tool 호출 요청"""
    name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Tool 호출 응답"""
    content: List[Dict[str, Any]]
    isError: bool = False


class JiraIssue(BaseModel):
    """Jira Issue 데이터"""
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    issue_type: Optional[str] = Field(None, alias="issueType")
    labels: List[str] = []
    components: List[str] = []


class ConfluencePage(BaseModel):
    """Confluence Page 데이터"""
    id: str
    title: str
    space: str
    content: Optional[str] = None
    version: Optional[int] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    author: Optional[str] = None
    labels: List[str] = []


class SearchResult(BaseModel):
    """검색 결과"""
    source: Literal["jira", "confluence"]
    item_id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    url: Optional[str] = None
