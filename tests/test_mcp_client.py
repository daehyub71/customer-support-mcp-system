"""
Unit Tests for MCP Client

MCP Client의 연결, 재시도, 타임아웃 로직을 검증하는 단위 테스트
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError, HTTPError

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp.mcp_client import MCPClient
from app.mcp.types import MCPResponse, Tool


class TestMCPClientConnection:
    """연결 관련 테스트"""

    @patch('app.mcp.mcp_client.requests.Session')
    def test_connect_success(self, mock_session_class):
        """연결 성공 케이스"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0.0"
                }
            }
        }
        mock_response.raise_for_status = Mock()

        # Mock session
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000, timeout=30)
        result = client.connect()

        assert result is True
        assert client.connected is True
        assert client.server_capabilities is not None
        mock_session.post.assert_called_once()

    @patch('app.mcp.mcp_client.requests.Session')
    @patch('app.mcp.mcp_client.time.sleep')  # Mock sleep to speed up test
    def test_connect_failure_with_retry(self, mock_sleep, mock_session_class):
        """연결 실패 케이스 - 3회 재시도 후 실패"""
        # Mock session that always fails
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("Connection refused")
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000, timeout=30)

        with pytest.raises(Exception) as exc_info:
            client.connect()

        assert "Failed to connect to MCP server" in str(exc_info.value)
        assert client.connected is False

        # Verify 3 attempts were made
        assert mock_session.post.call_count == 3

        # Verify sleep was called with correct delays (1s, 2s)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch('app.mcp.mcp_client.requests.Session')
    @patch('app.mcp.mcp_client.time.sleep')
    def test_connect_success_after_retry(self, mock_sleep, mock_session_class):
        """재시도 후 연결 성공 케이스"""
        # Mock response for successful connection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }
        mock_response.raise_for_status = Mock()

        # Mock session: fail twice, then succeed
        mock_session = Mock()
        mock_session.post.side_effect = [
            ConnectionError("Connection refused"),  # 1st attempt
            ConnectionError("Connection refused"),  # 2nd attempt
            mock_response                           # 3rd attempt (success)
        ]
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000, timeout=30)
        result = client.connect()

        assert result is True
        assert client.connected is True
        assert mock_session.post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('app.mcp.mcp_client.requests.Session')
    def test_disconnect(self, mock_session_class):
        """안전한 연결 종료 테스트"""
        # Mock successful connection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {}
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)
        client.connect()

        assert client.connected is True

        client.disconnect()

        assert client.connected is False
        mock_session.close.assert_called_once()


class TestMCPClientTimeout:
    """타임아웃 관련 테스트"""

    @patch('app.mcp.mcp_client.requests.Session')
    def test_timeout_during_connect(self, mock_session_class):
        """연결 시 타임아웃 발생"""
        # Mock session that times out
        mock_session = Mock()
        mock_session.post.side_effect = Timeout("Request timed out")
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000, timeout=5)

        with pytest.raises(Exception) as exc_info:
            client.connect()

        assert "Failed to connect" in str(exc_info.value)

    @patch('app.mcp.mcp_client.requests.Session')
    def test_timeout_configuration(self, mock_session_class):
        """타임아웃 설정 검증"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Test with custom timeout
        client = MCPClient(host="localhost", port=9000, timeout=10)
        assert client.timeout == 10

        # Test with default timeout
        client2 = MCPClient(host="localhost", port=9000)
        assert client2.timeout == 30


class TestMCPClientToolOperations:
    """Tool 호출 관련 테스트"""

    @patch('app.mcp.mcp_client.requests.Session')
    def test_list_tools_success(self, mock_session_class):
        """Tool 목록 조회 성공"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "tools": [
                    {
                        "name": "jira_search_issues",
                        "description": "Search Jira issues",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "jql": {
                                    "type": "string",
                                    "description": "JQL query"
                                },
                                "maxResults": {
                                    "type": "number",
                                    "description": "Max results"
                                }
                            },
                            "required": ["jql"]
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)
        tools = client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "jira_search_issues"
        assert tools[0].description == "Search Jira issues"
        assert len(tools[0].parameters) == 2

    @patch('app.mcp.mcp_client.requests.Session')
    def test_call_tool_success(self, mock_session_class):
        """Tool 호출 성공"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"key": "PROJ-123", "summary": "Test issue"}'
                    }
                ],
                "isError": False
            }
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)
        result = client.call_tool("jira_get_issue", {"issueKey": "PROJ-123"})

        assert result.isError is False
        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"

    @patch('app.mcp.mcp_client.requests.Session')
    def test_call_tool_error(self, mock_session_class):
        """Tool 호출 실패 - isError=True 반환"""
        # Mock error response from _send_request
        # call_tool catches exceptions and returns ToolCallResponse with isError=True
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {
                "code": -32602,
                "message": "Invalid params"
            }
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test - call_tool should catch exception and return error response
        client = MCPClient(host="localhost", port=9000)
        result = client.call_tool("invalid_tool", {})

        # Verify error response
        assert result.isError is True
        assert len(result.content) == 1
        assert "Error:" in result.content[0]["text"]
        assert "Invalid params" in result.content[0]["text"]


class TestMCPClientHealthCheck:
    """Health Check 관련 테스트"""

    @patch('app.mcp.mcp_client.requests.Session')
    def test_health_check_healthy(self, mock_session_class):
        """Health check 성공"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"tools": []}
        }
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)
        health = client.health_check()

        assert health["status"] == "healthy"
        assert health["error"] is None
        assert health["response_time_ms"] > 0

    @patch('app.mcp.mcp_client.requests.Session')
    def test_health_check_unhealthy(self, mock_session_class):
        """Health check 실패"""
        # Mock session that fails
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("Connection refused")
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)
        health = client.health_check()

        assert health["status"] == "unhealthy"
        assert health["error"] is not None
        assert "Connection refused" in health["error"]


class TestMCPClientRetryLogic:
    """재시도 로직 검증"""

    @patch('app.mcp.mcp_client.requests.Session')
    @patch('app.mcp.mcp_client.time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep, mock_session_class):
        """지수 백오프 지연 시간 검증 (1초, 2초, 4초)"""
        # Mock session that always fails
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("Connection refused")
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)

        try:
            client.connect()
        except Exception:
            pass

        # Verify sleep was called with correct delays
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2]  # 1초, 2초 (마지막 실패 후에는 sleep 안함)

    @patch('app.mcp.mcp_client.requests.Session')
    @patch('app.mcp.mcp_client.time.sleep')
    def test_max_retry_attempts(self, mock_sleep, mock_session_class):
        """최대 재시도 횟수 검증 (3회)"""
        # Mock session that always fails
        mock_session = Mock()
        mock_session.post.side_effect = ConnectionError("Connection refused")
        mock_session_class.return_value = mock_session

        # Test
        client = MCPClient(host="localhost", port=9000)

        with pytest.raises(Exception):
            client.connect()

        # Verify exactly 3 attempts
        assert mock_session.post.call_count == 3


class TestMCPClientEnvironmentVariables:
    """환경변수 관련 테스트"""

    @patch.dict(os.environ, {
        'MCP_SERVER_HOST': 'test.example.com',
        'MCP_SERVER_PORT': '8080',
        'MCP_SERVER_PROTOCOL': 'https',
        'MCP_BASE_PATH': '/api/mcp'
    })
    @patch('app.mcp.mcp_client.requests.Session')
    def test_env_var_configuration(self, mock_session_class):
        """환경변수 기반 설정 검증"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = MCPClient()

        assert client.server_url == "https://test.example.com:8080/api/mcp"

    @patch('app.mcp.mcp_client.requests.Session')
    def test_parameter_override_env_vars(self, mock_session_class):
        """파라미터가 환경변수보다 우선"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = MCPClient(host="custom.host", port=3000)

        assert "custom.host:3000" in client.server_url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
