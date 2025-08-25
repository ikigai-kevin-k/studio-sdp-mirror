#!/usr/bin/env python3
"""
Slack 設定測試腳本
用於驗證 Slack 憑證和設定是否正確
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_environment_variables():
    """Test if environment variables are set correctly"""
    print("🔍 檢查環境變數...")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    user_token = os.getenv("SLACK_USER_TOKEN")

    print(f"SLACK_WEBHOOK_URL: {'✅ 已設定' if webhook_url else '❌ 未設定'}")
    print(f"SLACK_BOT_TOKEN: {'✅ 已設定' if bot_token else '❌ 未設定'}")
    print(f"SLACK_USER_TOKEN: {'✅ 已設定' if user_token else '❌ 未設定'}")

    if webhook_url:
        print(f"   Webhook URL: {webhook_url[:50]}...")
    if bot_token:
        print(f"   Bot Token: {bot_token[:20]}...")
    if user_token:
        print(f"   User Token: {user_token[:20]}...")

    return bool(webhook_url or bot_token or user_token)


def test_slack_sdk_import():
    """Test if slack-sdk can be imported"""
    print("\n🔍 檢查 Slack SDK...")

    try:
        from slack_sdk import WebClient
        from slack_sdk.webhook import WebhookClient

        print("✅ slack-sdk 已安裝")
        return True
    except ImportError:
        print("❌ slack-sdk 未安裝")
        print("   請執行: pip install slack-sdk")
        return False


def test_requests_import():
    """Test if requests can be imported"""
    print("\n🔍 檢查 requests 套件...")

    try:
        import requests

        print("✅ requests 已安裝")
        return True
    except ImportError:
        print("❌ requests 未安裝")
        print("   請執行: pip install requests")
        return False


def test_slack_notifier_import():
    """Test if our slack notifier can be imported"""
    print("\n🔍 檢查 Slack Notifier 模組...")

    try:
        from slack_notifier import SlackNotifier

        print("✅ Slack Notifier 模組已載入")
        return True
    except ImportError as e:
        print(f"❌ Slack Notifier 模組載入失敗: {e}")
        return False


def test_webhook_connection():
    """Test webhook connection"""
    print("\n🔍 測試 Webhook 連線...")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 未設定 SLACK_WEBHOOK_URL")
        return False

    try:
        from slack_sdk.webhook import WebhookClient

        client = WebhookClient(webhook_url)
        print("✅ Webhook 客戶端創建成功")

        # Test with a simple message
        response = client.send(
            text="🧪 測試訊息 - 如果你看到這則訊息，設定就成功了！"
        )

        if response.status_code == 200:
            print("✅ Webhook 測試訊息發送成功！")
            return True
        else:
            print(f"❌ Webhook 測試失敗: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Webhook 測試錯誤: {e}")
        return False


def test_bot_token():
    """Test bot token"""
    print("\n🔍 測試 Bot Token...")

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        print("❌ 未設定 SLACK_BOT_TOKEN")
        return False

    try:
        from slack_sdk import WebClient

        client = WebClient(token=bot_token)

        # Test auth.test endpoint
        response = client.auth_test()

        if response["ok"]:
            print("✅ Bot Token 驗證成功")
            print(f"   Bot ID: {response.get('bot_id', 'N/A')}")
            print(f"   User ID: {response.get('user_id', 'N/A')}")
            print(f"   Team: {response.get('team', 'N/A')}")
            return True
        else:
            print(
                f"❌ Bot Token 驗證失敗: {response.get('error', 'Unknown error')}"
            )
            return False

    except Exception as e:
        print(f"❌ Bot Token 測試錯誤: {e}")
        return False


def test_user_token():
    """Test user token"""
    print("\n🔍 測試 User Token...")

    user_token = os.getenv("SLACK_USER_TOKEN")
    if not user_token:
        print("❌ 未設定 SLACK_USER_TOKEN")
        return False

    try:
        from slack_sdk import WebClient

        client = WebClient(token=user_token)

        # Test auth.test endpoint
        response = client.auth_test()

        if response["ok"]:
            print("✅ User Token 驗證成功")
            print(f"   User ID: {response.get('user_id', 'N/A')}")
            print(f"   Team: {response.get('team', 'N/A')}")
            return True
        else:
            print(
                f"❌ User Token 驗證失敗: {response.get('error', 'Unknown error')}"
            )
            return False

    except Exception as e:
        print(f"❌ User Token 測試錯誤: {e}")
        return False


def test_slack_notifier_functionality():
    """Test our slack notifier functionality"""
    print("\n🔍 測試 Slack Notifier 功能...")

    try:
        from slack_notifier import (
            SlackNotifier,
            send_error_to_slack,
            send_success_to_slack,
        )

        # Test notifier initialization
        notifier = SlackNotifier()
        print("✅ SlackNotifier 初始化成功")

        # Test simple message
        success = notifier.send_simple_message("🧪 功能測試訊息")
        if success:
            print("✅ 簡單訊息發送測試成功")
        else:
            print("❌ 簡單訊息發送測試失敗")

        # Test error notification
        error_success = send_error_to_slack(
            "測試錯誤訊息", "99999", "TEST-TABLE", "TEST-ENV"
        )
        if error_success:
            print("✅ 錯誤通知測試成功")
        else:
            print("❌ 錯誤通知測試失敗")

        # Test success notification
        success_notification = send_success_to_slack(
            "測試成功訊息", "TEST-ENV", "TEST-TABLE"
        )
        if success_notification:
            print("✅ 成功通知測試成功")
        else:
            print("❌ 成功通知測試失敗")

        return True

    except Exception as e:
        print(f"❌ Slack Notifier 功能測試錯誤: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Slack 設定測試開始")
    print("=" * 50)

    tests = [
        ("環境變數檢查", test_environment_variables),
        ("Slack SDK 檢查", test_slack_sdk_import),
        ("Requests 套件檢查", test_requests_import),
        ("Slack Notifier 模組檢查", test_slack_notifier_import),
        ("Webhook 連線測試", test_webhook_connection),
        ("Bot Token 測試", test_bot_token),
        ("User Token 測試", test_user_token),
        ("Slack Notifier 功能測試", test_slack_notifier_functionality),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 執行時發生錯誤: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 測試結果摘要")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n總計: {passed}/{total} 項測試通過")

    if passed == total:
        print("🎉 恭喜！所有測試都通過了，你的 Slack 設定完全正確！")
        return True
    elif passed >= total * 0.7:
        print("⚠️  大部分測試通過，但有一些問題需要解決")
        return False
    else:
        print("❌ 許多測試失敗，請檢查你的設定")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
