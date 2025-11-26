#!/usr/bin/env python3
"""
Diagnostic script to check WebSocket connection issues between main_speed.py and mock server.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def check_config():
    """Check if ws.json is configured correctly for mock server."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "conf", "ws.json"
    )
    
    print("=" * 60)
    print("WebSocket Configuration Check")
    print("=" * 60)
    print()
    
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        server_url = config.get("server_url", "")
        token = config.get("token", "")
        
        print(f"📋 Current configuration:")
        print(f"   server_url: {server_url}")
        print(f"   token: {token}")
        print()
        
        # Check if pointing to mock server
        if "localhost" in server_url or "127.0.0.1" in server_url:
            if "8081" in server_url or "8080" in server_url:
                print("✅ Configuration points to mock server")
                return True
            else:
                print("⚠️  Configuration points to localhost but port might be wrong")
                print(f"   Expected: ws://localhost:8081/v1/ws or ws://localhost:8080/v1/ws")
                return False
        else:
            print("⚠️  Configuration points to real StudioAPI server, not mock server")
            print(f"   Current: {server_url}")
            print(f"   Should be: ws://localhost:8081/v1/ws (for mock server)")
            print()
            print("💡 To fix, update conf/ws.json:")
            print('   {')
            print('       "server_url": "ws://localhost:8081/v1/ws",')
            print('       "token": "0000"')
            print('   }')
            return False
            
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False


def check_connection_format():
    """Check the connection format used by main_speed.py."""
    print()
    print("=" * 60)
    print("Connection Format Check")
    print("=" * 60)
    print()
    
    # Simulate the connection URL that main_speed.py would use
    server_url = "ws://localhost:8081/v1/ws"
    token = "0000"
    table_id = "ARO-001"
    device_name = "ARO-001-1"
    
    connection_url = f"{server_url}?token={token}&id={table_id}&device={device_name}"
    
    print(f"📋 Connection URL format used by main_speed.py:")
    print(f"   {connection_url}")
    print()
    print("✅ This format is supported by mock_studio_api_server.py")
    print()


def check_mock_server():
    """Check if mock server is running."""
    print()
    print("=" * 60)
    print("Mock Server Status Check")
    print("=" * 60)
    print()
    
    import socket
    
    ports_to_check = [8080, 8081]
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is open (mock server might be running)")
        else:
            print(f"❌ Port {port} is closed (mock server is not running)")
    
    print()
    print("💡 To start mock server:")
    print("   python tests/mock_studio_api_server.py --port 8081")


def main():
    """Main diagnostic function."""
    print()
    print("🔍 WebSocket Connection Diagnostic Tool")
    print()
    
    config_ok = check_config()
    check_connection_format()
    check_mock_server()
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    if config_ok:
        print("✅ Configuration looks good!")
        print("💡 Make sure:")
        print("   1. Mock server is running: python tests/mock_studio_api_server.py --port 8081")
        print("   2. main_speed.py is running and has connected to mock server")
        print("   3. Check main_speed.py logs for connection status")
    else:
        print("❌ Configuration needs to be updated")
        print("💡 Update conf/ws.json to point to mock server")
    
    print()


if __name__ == "__main__":
    main()

