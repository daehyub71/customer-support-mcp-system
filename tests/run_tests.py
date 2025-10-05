"""
간단한 테스트 실행 스크립트

의존성 설치 후 이 스크립트를 실행하여 테스트를 검증할 수 있습니다.
"""
import subprocess
import sys

def main():
    """Run MCP Client tests"""

    print("=" * 80)
    print("MCP Client Unit Tests")
    print("=" * 80)
    print()

    # Check if dependencies are installed
    try:
        import pytest
        import requests
        print("✅ Dependencies check passed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return 1

    print()

    # Run tests
    test_commands = [
        ("All tests", ["pytest", "tests/test_mcp_client.py", "-v"]),
        ("Connection tests", ["pytest", "tests/test_mcp_client.py::TestMCPClientConnection", "-v"]),
        ("Retry logic tests", ["pytest", "tests/test_mcp_client.py::TestMCPClientRetryLogic", "-v"]),
    ]

    for name, cmd in test_commands:
        print(f"\n{'=' * 80}")
        print(f"Running: {name}")
        print(f"{'=' * 80}")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"\n❌ {name} failed")
            return result.returncode
        print(f"\n✅ {name} passed")

    print("\n" + "=" * 80)
    print("All tests passed! 🎉")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
