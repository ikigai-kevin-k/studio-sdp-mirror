#!/usr/bin/env python3
"""
Test script for Slack notification functionality for deal_post json parse error
"""

import time
from datetime import datetime
from slack import send_error_to_slack


def test_slack_notification():
    """Test Slack notification with different error scenarios"""

    print("🧪 Testing Slack notification functionality...")

    # Test 1: JSON parsing error for PRD
    print("\n📋 Test 1: PRD JSON parsing error")
    try:
        error_msg = (
            "Description: JSON parsing error in deal_post\n"
            "Details: Expecting value: line 1 column 1 (char 0)\n"
        )
        result = send_error_to_slack(
            error_message=error_msg,
            environment="PRD",
            table_name="SBO-001",
            error_code="JSON_PARSE_ERROR",
        )
        print(f"✅ PRD notification result: {result}")
    except Exception as e:
        print(f"❌ PRD notification failed: {e}")

    # Wait a bit between tests
    time.sleep(2)

    # Test 2: JSON parsing error for STG
    print("\n📋 Test 2: STG JSON parsing error")
    try:
        error_msg = (
            "Description: JSON parsing error in finish_round\n"
            "Details: Expecting value: line 1 column 1 (char 0)\n"
        )
        result = send_error_to_slack(
            error_message=error_msg,
            environment="STG",
            table_name="SBO-001",
            error_code="JSON_PARSE_ERROR",
        )
        print(f"✅ STG notification result: {result}")
    except Exception as e:
        print(f"❌ STG notification failed: {e}")

    # Wait a bit between tests
    time.sleep(2)

    # Test 3: Regular error (should not trigger special handling)
    print("\n📋 Test 3: Regular error (non-JSON parsing)")
    try:
        error_msg = (
            "Description: Network timeout\n"
            "Details: Connection timed out after 30 seconds\n"
        )
        result = send_error_to_slack(
            error_message=error_msg,
            environment="UAT",
            table_name="SBO-001",
            error_code="NETWORK_TIMEOUT",
        )
        print(f"✅ UAT notification result: {result}")
    except Exception as e:
        print(f"❌ UAT notification failed: {e}")

    print("\n🎯 Test completed!")
    print("\n📝 Notes:")
    print(
        "- PRD and STG JSON parsing errors should trigger Slack notifications"
    )
    print(
        "- Other errors will still be logged but won't have special handling"
    )
    print("- Check your Slack channel for the test messages")


if __name__ == "__main__":
    test_slack_notification()
