#!/usr/bin/env python3
"""
診斷 Slack 客戶端初始化問題
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """主診斷函數"""
    print("=== 環境變數檢查 ===")
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    user_token = os.getenv('SLACK_USER_TOKEN')
    
    print(f"SLACK_WEBHOOK_URL: {webhook_url[:50] if webhook_url else 'None'}")
    print(f"SLACK_BOT_TOKEN: {bot_token[:20] if bot_token else 'None'}")
    print(f"SLACK_USER_TOKEN: {user_token[:20] if user_token else 'None'}")

    print("\n=== 導入檢查 ===")
    try:
        from slack_sdk import WebClient
        print("✅ WebClient 導入成功")
    except ImportError as e:
        print(f"❌ WebClient 導入失敗: {e}")

    try:
        from slack_sdk.webhook import WebhookClient
        print("✅ WebhookClient 導入成功")
    except ImportError as e:
        print(f"❌ WebhookClient 導入失敗: {e}")

    try:
        from slack_notifier import SLACK_SDK_AVAILABLE
        print(f"✅ SLACK_SDK_AVAILABLE: {SLACK_SDK_AVAILABLE}")
    except ImportError as e:
        print(f"❌ SLACK_SDK_AVAILABLE 導入失敗: {e}")

    print("\n=== 客戶端創建測試 ===")
    try:
        if webhook_url:
            webhook_client = WebhookClient(webhook_url)
            print("✅ WebhookClient 創建成功")
        else:
            print("❌ 未設定 SLACK_WEBHOOK_URL")
    except Exception as e:
        print(f"❌ WebhookClient 創建失敗: {e}")

    try:
        if bot_token:
            bot_client = WebClient(token=bot_token)
            print("✅ BotClient 創建成功")
        else:
            print("❌ 未設定 SLACK_BOT_TOKEN")
    except Exception as e:
        print(f"❌ BotClient 創建失敗: {e}")

    print("\n=== SlackNotifier 測試 ===")
    try:
        from slack_notifier import SlackNotifier
        notifier = SlackNotifier()
        print("✅ SlackNotifier 創建成功")
        print(f"   webhook_client: {notifier.webhook_client is not None}")
        print(f"   bot_client: {notifier.bot_client is not None}")
        print(f"   user_client: {notifier.user_client is not None}")
        
        if notifier.webhook_client:
            success = notifier.send_simple_message("🎯 測試訊息")
            if success:
                print("✅ 我們的 Notifier 測試成功！")
            else:
                print("❌ 我們的 Notifier 測試失敗！")
        else:
            print("❌ Webhook client 未初始化")
            
    except Exception as e:
        print(f"❌ SlackNotifier 創建失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
