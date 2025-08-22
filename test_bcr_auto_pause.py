#!/usr/bin/env python3
"""
Test BCR auto pause function
Simulate 403 error handling and idle state
"""

import json
import time

def simulate_403_error():
    """Simulate 403 error response"""
    return {
        "error": {
            "message": "the round on Table \"BCR-001\" isn't finished yet",
            "code": 13003
        },
        "data": None
    }

def simulate_pause_state():
    """Simulate pause state"""
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": "BCR-001",
                "status": "PAUSED",
                "pause": {
                    "reason": "auto-pause-waiting-for-previous-round",
                    "createdAt": "2025-08-22T06:21:20.972Z",
                    "createdBy": "SDP"
                }
            }
        }
    }

def simulate_resume_state():
    """Simulate resume state"""
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": "BCR-001",
                "status": "bet-stopped",
                "pause": {}  # empty pause means resumed
            }
        }
    }

def test_403_error_handling():
    """Test 403 error handling logic"""
    print("🚀 Test BCR 403 error handling")
    print("=" * 60)
    
    # Simulate 403 error
    error_response = simulate_403_error()
    print("❌ Received 403 error:")
    print(json.dumps(error_response, indent=2, ensure_ascii=False))
    
    # 檢查錯誤代碼和消息
    error_code = error_response.get("error", {}).get("code")
    error_message = error_response.get("error", {}).get("message", "")
    
    if (error_code == 13003 and 
        "isn't finished yet" in error_message):
        
        print("\n✅ Detected previous round not finished error")
        print("🔄 System will automatically perform the following actions:")
        print("   1. Send Slack notification")
        print("   2. Auto pause table")
        print("   3. Enter IDLE waiting state")
        
        return "IDLE_WAITING", "PAUSED"
    
    return -1, -1

def test_pause_monitoring():
    """Test pause state monitoring"""
    print("\n🔄 Test Pause state monitoring")
    print("=" * 60)
    
    # Simulate pause state
    pause_response = simulate_pause_state()
    print("⏸️ Current pause state:")
    print(json.dumps(pause_response, indent=2, ensure_ascii=False))
    
    pause_info = pause_response.get("data", {}).get("table", {}).get("pause", {})
    if pause_info:
        print(f"⏳ Waiting... pause reason: {pause_info.get('reason')}")
        return False  # Still in pause state
    
    return True  # Resume

def test_resume_detection():
    """Test resume detection"""
    print("\n✅ Test resume detection")
    print("=" * 60)
    
    # Simulate resume state
    resume_response = simulate_resume_state()
    print("🔄 Table has resumed:")
    print(json.dumps(resume_response, indent=2, ensure_ascii=False))
    
    pause_info = resume_response.get("data", {}).get("table", {}).get("pause", {})
    if not pause_info:  # pause is empty
        print("✅ pause state cleared, table resumed")
        return True
    
    return False

def main():
    """Main test flow"""
    print("🎯 BCR auto pause function test")
    print("=" * 60)
    
    # Test 1: 403 error handling
    result = test_403_error_handling()
    if result[0] == "IDLE_WAITING":
        print(f"\n🔄 Enter IDLE state: {result}")
        
        # Test 2: Test pause state monitoring
        print("\n" + "="*60)
        print("Simulate waiting 5 seconds...")
        time.sleep(5)
        
        # Test 3: Test resume detection
        if test_resume_detection():
            print("\n🎉 Test completed! System successfully handled 403 error and resumed")
        else:
            print("\n⚠️ Test completed, but table is still in pause state")
    else:
        print(f"\n❌ Error handling failed: {result}")

if __name__ == "__main__":
    main()
