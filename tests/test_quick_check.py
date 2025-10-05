"""
빠른 검증용 간단한 테스트

의존성 없이 기본 구조만 검증
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_import_mcp_types():
    """MCP types module import test"""
    try:
        from app.mcp.types import (
            Tool,
            Resource,
            MCPRequest,
            MCPResponse,
            JiraIssue,
            ConfluencePage,
        )
        print("[OK] MCP types import successful")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import MCP types: {e}")
        return False

def test_import_mcp_client():
    """MCP client module import test"""
    try:
        from app.mcp.mcp_client import MCPClient
        print("[OK] MCP client import successful")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import MCP client: {e}")
        return False

def test_import_config():
    """Config module import test"""
    try:
        from app.utils.config import Config, config
        print("[OK] Config import successful")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import config: {e}")
        return False

def test_client_initialization():
    """Client initialization test (no network)"""
    try:
        from app.mcp.mcp_client import MCPClient

        # Test with parameters
        client = MCPClient(host="localhost", port=9000, timeout=30)
        assert client.timeout == 30
        assert "localhost:9000" in client.server_url

        print("[OK] Client initialization successful")
        print(f"   Server URL: {client.server_url}")
        print(f"   Timeout: {client.timeout}s")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to initialize client: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_values():
    """Config values check"""
    try:
        from app.utils.config import config

        print("[OK] Config values:")
        print(f"   MCP_SERVER_HOST: {config.MCP_SERVER_HOST}")
        print(f"   MCP_SERVER_PORT: {config.MCP_SERVER_PORT}")
        print(f"   MCP_TIMEOUT: {config.MCP_TIMEOUT}")
        print(f"   Full URL: {config.get_mcp_server_url()}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to check config: {e}")
        return False

def main():
    """Run quick tests"""
    print("=" * 80)
    print("MCP Client Quick Check")
    print("=" * 80)
    print()

    tests = [
        test_import_mcp_types,
        test_import_mcp_client,
        test_import_config,
        test_client_initialization,
        test_config_values,
    ]

    results = []
    for test in tests:
        print(f"\nRunning: {test.__name__}")
        print("-" * 80)
        result = test()
        results.append(result)
        print()

    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All quick checks passed!")
        return 0
    else:
        print("[ERROR] Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
