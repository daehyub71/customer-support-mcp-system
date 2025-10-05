# app/mcp/mcp_client.py
"""
MCP Client Implementation

Atlassian MCP Server와 통신하는 클라이언트 모듈
- HTTP/STDIO 프로토콜 지원
- Tool 호출 및 리소스 접근
- 연결 관리 및 에러 핸들링
"""
import os
import json
import uuid
import logging
import time
from typing import Dict, List, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .types import (
    MCPRequest,
    MCPResponse,
    Tool,
    Resource,
    ToolCallResponse,
    JiraIssue,
    ConfluencePage,
)

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Protocol Client for Atlassian"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: int = 30,
        server_url: Optional[str] = None,
        protocol: str = "http",
    ):
        """
        Initialize MCP Client

        Args:
            host: MCP server host (default: from env MCP_SERVER_HOST)
            port: MCP server port (default: from env MCP_SERVER_PORT)
            timeout: Request timeout in seconds (default: 30)
            server_url: Full MCP server URL (overrides host/port)
            protocol: 'http' or 'stdio'
        """
        self.protocol = protocol
        self.timeout = timeout
        self.connected = False
        self.server_capabilities: Optional[Dict[str, Any]] = None
        self.session_id: Optional[str] = None  # ← 헤더로 주고받는 세션 ID

        # Load configuration from environment or parameters
        if server_url:
            self.server_url = server_url
        else:
            _host = host or os.getenv("MCP_SERVER_HOST", "localhost")
            _port = port or os.getenv("MCP_SERVER_PORT", "9000")
            _protocol = os.getenv("MCP_SERVER_PROTOCOL", "http")
            base_path = os.getenv("MCP_BASE_PATH", "/mcp")
            # 서버는 /mcp 또는 /mcp/ 모두 처리하지만, 여기선 트레일링 슬래시 없이 둠
            self.server_url = f"{_protocol}://{_host}:{_port}{base_path}"

        # HTTP session with retry logic (exponential backoff: 1s, 2s, 4s)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s * 2^retry_num = 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"MCP Client initialized: {self.server_url}")

    # -----------------------------
    # Low-level request primitives
    # -----------------------------
    def _make_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            # 서버가 application/json 과 text/event-stream 을 모두 Accept 하길 요구
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            # ★ 핵심: 세션은 헤더로 넘긴다
            headers["mcp-session-id"] = self.session_id
        return headers

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """
        Send MCP request to server

        Args:
            method: MCP method name
            params: Method parameters (None면 params 제거)

        Returns:
            MCPResponse object
        """
        request_data: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
        }
        if params is not None:
            request_data["params"] = params

        request_model = MCPRequest(**request_data)
        request_json = request_model.model_dump(exclude_none=True)

        try:
            headers = self._make_headers()
            logger.debug("-> %s %s | headers=%s", method, params, headers)

            # 일부 서버는 /mcp 로 보내면 307 리다이렉트로 /mcp/ 응답.
            # requests가 자동 따름. 여기서는 원 URL 유지.
            resp = self.session.post(
                self.server_url,
                json=request_json,
                timeout=self.timeout,
                headers=headers,
            )
            resp.raise_for_status()

            # ★ 응답 헤더에서 세션ID 갱신
            sid = resp.headers.get("mcp-session-id")
            if sid:
                self.session_id = sid
                logger.debug("Stored MCP session ID: %s", self.session_id)

            content_type = (resp.headers.get("Content-Type") or "").lower()

            # SSE 응답 처리
            if "text/event-stream" in content_type:
                logger.debug("SSE response head (200 chars): %r", resp.text[:200])
                data = self._parse_sse_response(resp.text)
            else:
                data = resp.json()

            logger.debug("<- response: %s", data)
            mcp_response = MCPResponse(**data)

            if mcp_response.error:
                logger.error("MCP Error: %s", mcp_response.error)
                raise Exception(f"MCP Error: {mcp_response.error.get('message', mcp_response.error)}")

            return mcp_response

        except requests.exceptions.JSONDecodeError as e:
            logger.error(
                "Non-JSON response | status=%s | headers=%s | text=%r",
                getattr(resp, "status_code", "?"),
                dict(getattr(resp, "headers", {})),
                (getattr(resp, "text", "") or "")[:1000],
            )
            raise Exception(f"Failed to communicate with MCP server: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            raise Exception(f"Failed to communicate with MCP server: {e}") from e

    @staticmethod
    def _parse_sse_response(sse_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events (SSE) response format: lines of `event:` and `data:`"""
        # 가장 최근 data: 라인을 파싱
        data_obj: Optional[Dict[str, Any]] = None
        for raw_line in sse_text.splitlines():
            line = raw_line.strip()
            if line.lower().startswith("data:"):
                payload = line[5:].lstrip()  # remove "data:" and following space
                try:
                    data_obj = json.loads(payload)
                except Exception:
                    # 혹시 단일 JSON이 아닌 경우를 대비해 마지막 data만 사용
                    pass
        if data_obj is None:
            # 혹시 통째로 JSON일 수 있으니 한 번 더 시도
            data_obj = json.loads(sse_text)
        return data_obj

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a notification (no response expected)"""
        notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            notification["params"] = params

        try:
            headers = self._make_headers()
            self.session.post(
                self.server_url,
                json=notification,
                timeout=self.timeout,
                headers=headers,
            )
            logger.debug("Sent notification: %s", method)
        except Exception as e:
            logger.warning("Failed to send notification %s: %s", method, e)

    # -----------------------------
    # Connection lifecycle
    # -----------------------------
    def connect(self) -> bool:
        """
        Establish connection to MCP server with retry logic

        Returns:
            True if connected successfully

        Raises:
            Exception: If connection fails after retries
        """
        retry_delays = [1, 2, 4]  # Exponential backoff

        for attempt, delay in enumerate(retry_delays, 1):
            try:
                logger.info("Connecting to MCP server (attempt %d/%d)...", attempt, len(retry_delays))

                resp = self._send_request(
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            # 서버가 요구하는 capability 최소 셋
                            "roots": {"listChanged": True},
                            "sampling": {},
                        },
                        "clientInfo": {"name": "customer-support-mcp-client", "version": "1.0.0"},
                    },
                )

                # 서버 capabilities 저장
                self.server_capabilities = resp.result or {}

                # 초기화 완료 알림 (필요한 서버가 있음)
                self._send_notification("notifications/initialized")

                self.connected = True
                logger.info("MCP connection established successfully (session=%s)", self.session_id)
                return True

            except Exception as e:
                logger.warning("Connection attempt %d failed: %s", attempt, e)
                if attempt < len(retry_delays):
                    logger.info("Retrying in %d seconds...", delay)
                    time.sleep(delay)
                else:
                    logger.error("Failed to connect to MCP server after %d attempts", len(retry_delays))
                    raise Exception(f"Failed to connect to MCP server: {e}") from e

        return False

    def disconnect(self) -> None:
        """Safely disconnect from MCP server"""
        try:
            if self.connected:
                try:
                    # ★ 이 서버는 세션을 헤더로만 요구 → params 없이 shutdown
                    self._send_request("shutdown", None)
                except Exception as e:
                    logger.warning("MCP Error on shutdown: %s", e)
                finally:
                    self.connected = False
                    logger.info("MCP connection closed")
        finally:
            try:
                if self.session:
                    self.session.close()
            except Exception:
                pass

    # -----------------------------
    # Convenience helpers
    # -----------------------------
    def health_check(self) -> Dict[str, Any]:
        """
        Check MCP server health status
        """
        start = time.time()
        out = {
            "status": "unhealthy",
            "server_url": self.server_url,
            "connected": self.connected,
            "response_time_ms": 0.0,
            "error": None,
        }
        try:
            resp = self._send_request("tools/list", None)
            dt = (time.time() - start) * 1000.0
            if resp and not resp.error:
                out["status"] = "healthy"
                out["response_time_ms"] = round(dt, 2)
                logger.info("Health check passed (%.2f ms)", dt)
            else:
                out["error"] = str(resp.error) if resp else "Unknown error"
        except Exception as e:
            out["error"] = str(e)
            logger.error("Health check failed: %s", e)
        return out

    def initialize(self) -> Dict[str, Any]:
        """Initialize MCP connection (alias for connect)"""
        self.connect()
        return self.server_capabilities or {}

    # -----------------------------
    # Tools/Resources
    # -----------------------------
    def list_tools(self) -> List[Tool]:
        """List available tools from MCP server"""
        try:
            # tools/list 는 params 없음
            resp = self._send_request("tools/list", None)
            tools_data = resp.result.get("tools", []) if resp.result else []
            tools: List[Tool] = []

            for t in tools_data:
                schema = t.get("inputSchema", {}) or {}
                properties = schema.get("properties", {}) or {}
                required = schema.get("required", []) or []

                parameters = []
                for name, info in properties.items():
                    parameters.append({
                        "name": name,
                        "type": info.get("type", "string"),
                        "description": info.get("description", ""),
                        "required": name in required,
                        "enum": info.get("enum"),
                    })

                tools.append(Tool(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=parameters,
                ))

            logger.info("Retrieved %d tools from MCP server", len(tools))
            return tools
        except Exception as e:
            logger.error("Failed to list tools: %s", e)
            return []

    def list_resources(self) -> List[Resource]:
        """List available resources from MCP server"""
        try:
            resp = self._send_request("resources/list", None)
            resources_data = resp.result.get("resources", []) if resp.result else []
            resources = [Resource(**r) for r in resources_data]
            logger.info("Retrieved %d resources from MCP server", len(resources))
            return resources
        except Exception as e:
            logger.error("Failed to list resources: %s", e)
            return []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolCallResponse:
        """Call a tool on MCP server"""
        try:
            resp = self._send_request("tools/call", {"name": name, "arguments": arguments})
            result = resp.result or {}
            return ToolCallResponse(content=result.get("content", []), isError=result.get("isError", False))
        except Exception as e:
            logger.error("Failed to call tool %s: %s", name, e)
            return ToolCallResponse(content=[{"type": "text", "text": f"Error: {e}"}], isError=True)

    def read_resource(self, uri: str) -> Optional[str]:
        """Read a resource from MCP server"""
        try:
            resp = self._send_request("resources/read", {"uri": uri})
            result = resp.result or {}
            contents = result.get("contents", [])
            if contents:
                return contents[0].get("text") or contents[0].get("blob")
            return None
        except Exception as e:
            logger.error("Failed to read resource %s: %s", uri, e)
            return None

    # -----------------------------
    # High-level Jira/Confluence helpers
    # -----------------------------
    def search_jira_issues(
        self,
        jql: Optional[str] = None,
        project: Optional[str] = None,
        status: Optional[str] = None,
        max_results: int = 50,
    ) -> List[JiraIssue]:
        """Search Jira issues"""
        args: Dict[str, Any] = {"maxResults": max_results}

        if jql:
            args["jql"] = jql
        else:
            conditions = []
            if project:
                conditions.append(f"project = {project}")
            if status:
                conditions.append(f"status = '{status}'")
            args["jql"] = " AND ".join(conditions) if conditions else "ORDER BY updated DESC"

        resp = self.call_tool("jira_search_issues", args)
        if resp.isError:
            logger.error("Jira search failed: %s", resp.content)
            return []

        issues: List[JiraIssue] = []
        for item in resp.content:
            if item.get("type") == "text":
                try:
                    data = json.loads(item["text"])
                    if isinstance(data, list):
                        for d in data:
                            issues.append(JiraIssue(**d))
                    elif isinstance(data, dict):
                        issues.append(JiraIssue(**data))
                except Exception as e:
                    logger.warning("Failed to parse Jira issue: %s", e)
        return issues

    def get_jira_issue(self, issue_key: str) -> Optional[JiraIssue]:
        """Get a specific Jira issue"""
        resp = self.call_tool("jira_get_issue", {"issueKey": issue_key})
        if resp.isError:
            logger.error("Failed to get Jira issue %s", issue_key)
            return None
        for item in resp.content:
            if item.get("type") == "text":
                try:
                    data = json.loads(item["text"])
                    return JiraIssue(**data)
                except Exception as e:
                    logger.warning("Failed to parse Jira issue: %s", e)
        return None

    def search_confluence_pages(
        self,
        query: str,
        space: Optional[str] = None,
        max_results: int = 50,
    ) -> List[ConfluencePage]:
        """Search Confluence pages"""
        args: Dict[str, Any] = {"cql": f"text ~ '{query}'", "limit": max_results}
        if space:
            args["cql"] = f"space = {space} AND {args['cql']}"

        resp = self.call_tool("confluence_search", args)
        if resp.isError:
            logger.error("Confluence search failed: %s", resp.content)
            return []

        pages: List[ConfluencePage] = []
        for item in resp.content:
            if item.get("type") == "text":
                try:
                    data = json.loads(item["text"])
                    if isinstance(data, list):
                        for d in data:
                            pages.append(ConfluencePage(**d))
                    elif isinstance(data, dict):
                        pages.append(ConfluencePage(**data))
                except Exception as e:
                    logger.warning("Failed to parse Confluence page: %s", e)
        return pages

    def get_confluence_page(self, page_id: str) -> Optional[ConfluencePage]:
        """Get a specific Confluence page"""
        resp = self.call_tool("confluence_get_page", {"pageId": page_id})
        if resp.isError:
            logger.error("Failed to get Confluence page %s", page_id)
            return None
        for item in resp.content:
            if item.get("type") == "text":
                try:
                    data = json.loads(item["text"])
                    return ConfluencePage(**data)
                except Exception as e:
                    logger.warning("Failed to parse Confluence page: %s", e)
        return None

    def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            self.session.close()
        logger.info("MCP connection closed")
