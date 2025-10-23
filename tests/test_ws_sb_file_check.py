"""
Simple file existence and content tests for ws_sb.py module.

This module tests basic file structure without complex imports.
"""

import json
from pathlib import Path


def test_ws_sb_file_exists():
    """Test that ws_sb.py file exists and is readable."""
    ws_sb_path = Path("studio_api/ws_sb.py")
    assert ws_sb_path.exists(), "ws_sb.py file not found"

    # Try to read the file
    with open(ws_sb_path, "r") as f:
        content = f.read()

    # Verify it contains expected content
    assert "test_sbo_001_device_info" in content
    assert "main" in content
    assert "async def" in content


def test_ws_client_file_exists():
    """Test that ws_client.py file exists and is readable."""
    ws_client_path = Path("studio_api/ws_client.py")
    assert ws_client_path.exists(), "ws_client.py file not found"

    # Try to read the file
    with open(ws_client_path, "r") as f:
        content = f.read()

    # Verify it contains expected content
    assert "SmartStudioWebSocketClient" in content
    assert "StudioServiceStatusEnum" in content
    assert "StudioMaintenanceStatusEnum" in content


def test_ws_json_config_exists():
    """Test that ws.json configuration file exists and is valid JSON."""
    config_path = Path("conf/ws.json")
    assert config_path.exists(), "ws.json configuration file not found"

    with open(config_path, "r") as f:
        config = json.load(f)

    # Verify required keys exist
    assert "server_url" in config
    assert "device_name" in config
    assert "token" in config
    assert "tables" in config

    # Verify server_url is a valid WebSocket URL
    assert config["server_url"].startswith(("ws://", "wss://"))

    # Verify tables is a list
    assert isinstance(config["tables"], list)

    # Verify at least one table exists
    assert len(config["tables"]) > 0


def test_sbo_001_table_config():
    """Test specific structure for SBO-001 table."""
    config_path = Path("conf/ws.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Test specific structure for SBO-001 table
    sbo_table = None
    for table in config["tables"]:
        if table["table_id"] == "SBO-001":
            sbo_table = table
            break

    assert sbo_table is not None, "SBO-001 table not found in configuration"
    assert sbo_table["name"] == "SBO-001"


def test_ws_sb_syntax_valid():
    """Test that ws_sb.py has valid Python syntax."""
    ws_sb_path = Path("studio_api/ws_sb.py")

    with open(ws_sb_path, "r") as f:
        content = f.read()

    # Basic syntax check - try to compile
    try:
        compile(content, ws_sb_path, "exec")
    except SyntaxError as e:
        assert False, f"Syntax error in ws_sb.py: {e}"


def test_ws_client_syntax_valid():
    """Test that ws_client.py has valid Python syntax."""
    ws_client_path = Path("studio_api/ws_client.py")

    with open(ws_client_path, "r") as f:
        content = f.read()

    # Basic syntax check - try to compile
    try:
        compile(content, ws_client_path, "exec")
    except SyntaxError as e:
        assert False, f"Syntax error in ws_client.py: {e}"


def test_websockets_import_available():
    """Test that websockets dependency is available."""
    try:
        import websockets

        assert websockets is not None
    except ImportError:
        assert False, "websockets module not available"


def test_asyncio_available():
    """Test that asyncio is available."""
    import asyncio

    assert asyncio is not None


def test_python_version_compatibility():
    """Test Python version compatibility."""
    import sys

    # Check if Python version is 3.7+ (for async/await support)
    assert sys.version_info >= (3, 7), "Python 3.7+ required for async/await"


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_ws_sb_file_exists,
        test_ws_client_file_exists,
        test_ws_json_config_exists,
        test_sbo_001_table_config,
        test_ws_sb_syntax_valid,
        test_ws_client_syntax_valid,
        test_websockets_import_available,
        test_asyncio_available,
        test_python_version_compatibility,
    ]

    passed = 0
    total = len(test_functions)

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}: PASSED")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: FAILED - {e}")

    print(f"\nTest Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        exit(0)
    else:
        print("❌ Some tests failed!")
        exit(1)
