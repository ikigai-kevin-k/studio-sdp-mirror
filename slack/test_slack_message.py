#!/usr/bin/env python3
"""
Simple Slack Message Test Script
Test Script for Sending Messages to Slack
"""

from slack_notifier import (
    SlackNotifier,
    send_error_to_slack,
    send_success_to_slack,
)


def test_simple_message():
    """Test Sending Simple Message"""
    print("🧪 Testing Simple Message...")

    notifier = SlackNotifier()
    success = notifier.send_simple_message("🎲 From SDP : Testing Message！")

    if success:
        print("✅ Simple Message Sent Successfully！")
    else:
        print("❌ Simple Message Failed to Send!")

    return success


def test_error_notification():
    """Test Sending Error Notification"""
    print("\n🚨 Testing Error Notification...")

    success = send_error_to_slack(
        error_message="Testing Error: Table round not finished yet",
        error_code="13003",
        table_name="SBO-001",
        environment="STG",
    )

    if success:
        print("✅ Error Notification Sent Successfully!")
    else:
        print("❌ Error Notification Failed to Send!")

    return success


def test_success_notification():
    """Test Sending Success Notification"""
    print("\n✅ Testing Success Notification...")

    success = send_success_to_slack(
        message="Testing Success: Table operation completed",
        environment="PRD",
        table_name="ARO-001",
    )

    if success:
        print("✅ Success Notification Sent Successfully!")
    else:
        print("❌ Success Notification Failed to Send!")

    return success


def test_rich_message():
    """Test Sending Rich Message"""
    print("\n🎨 Testing Rich Message...")

    notifier = SlackNotifier()

    # 創建豐富的訊息區塊
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🎯 SDP System Status",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This is a test message, demonstrating rich formatting features",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Status:*\n🟢 Running"},
                {"type": "mrkdwn", "text": "*Environment:*\nSTG"},
            ],
        },
    ]

    success = notifier.send_rich_message(
        channel="#ge-studio",  # 使用 Bot Token 發送到指定頻道
        blocks=blocks,
        text="SDP System Status Update",
    )

    if success:
        print("✅ Rich Message Sent Successfully!")
    else:
        print("❌ Rich Message Failed to Send!")

    return success


def main():
    """Main Test Function"""
    print("🚀 Slack Message Sending Test Started")
    print("=" * 50)

    tests = [
        ("Simple Message Test", test_simple_message),
        ("Error Notification Test", test_error_notification),
        ("Success Notification Test", test_success_notification),
        ("Rich Message Test", test_rich_message),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} Error Occurred: {e}")
            results.append((test_name, False))

    # 總結
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ Success" if result else "❌ Failed"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{total} Tests Passed")

    if passed == total:
        print(
            "🎉 Congratulations! All messages were successfully sent to Slack!"
        )
        print(
            "Please check your Slack channel to confirm messages were received."
        )
    else:
        print("⚠️  Some tests failed, please check the error messages.")

    return passed == total


if __name__ == "__main__":
    main()
