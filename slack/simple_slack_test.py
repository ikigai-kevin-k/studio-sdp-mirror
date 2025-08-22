#!/usr/bin/env python3
"""
簡單的 Slack 測試腳本
直接使用環境變數測試
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_direct_webhook():
    """直接測試 webhook"""
    print("🧪 直接測試 Webhook...")
    
    try:
        from slack_sdk.webhook import WebhookClient
        
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            print("❌ 未設定 SLACK_WEBHOOK_URL")
            return False
        
        client = WebhookClient(webhook_url)
        response = client.send("🎲 直接 Webhook 測試訊息！")
        
        if response.status_code == 200:
            print("✅ Webhook 測試成功！")
            return True
        else:
            print(f"❌ Webhook 測試失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook 測試錯誤: {e}")
        return False

def test_direct_bot():
    """直接測試 bot"""
    print("\n🤖 直接測試 Bot...")
    
    try:
        from slack_sdk import WebClient
        
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        if not bot_token:
            print("❌ 未設定 SLACK_BOT_TOKEN")
            return False
        
        client = WebClient(token=bot_token)
        
        # 先測試認證
        auth_response = client.auth_test()
        if not auth_response["ok"]:
            print(f"❌ Bot 認證失敗: {auth_response.get('error')}")
            return False
        
        print(f"✅ Bot 認證成功: {auth_response.get('user_id')}")
        
        # 嘗試發送訊息到頻道
        # 注意：這裡需要一個存在的頻道名稱
        response = client.chat_postMessage(
            channel="#general",  # 或者使用頻道 ID
            text="🤖 直接 Bot 測試訊息！"
        )
        
        if response["ok"]:
            print("✅ Bot 訊息發送成功！")
            return True
        else:
            print(f"❌ Bot 訊息發送失敗: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Bot 測試錯誤: {e}")
        return False

def test_our_notifier():
    """測試我們的 notifier"""
    print("\n🔧 測試我們的 Notifier...")
    
    try:
        from slack_notifier import SlackNotifier
        
        # 直接傳入參數
        notifier = SlackNotifier(
            webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            bot_token=os.getenv('SLACK_BOT_TOKEN'),
            user_token=os.getenv('SLACK_USER_TOKEN')
        )
        
        print(f"   webhook_client: {notifier.webhook_client is not None}")
        print(f"   bot_client: {notifier.bot_client is not None}")
        print(f"   user_client: {notifier.user_client is not None}")
        
        if notifier.webhook_client:
            success = notifier.send_simple_message("🎯 我們的 Notifier 測試訊息！")
            if success:
                print("✅ 我們的 Notifier 測試成功！")
                return True
            else:
                print("❌ 我們的 Notifier 測試失敗！")
                return False
        else:
            print("❌ Webhook client 未初始化")
            return False
            
    except Exception as e:
        print(f"❌ 我們的 Notifier 測試錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主測試函數"""
    print("🚀 直接 Slack 測試開始")
    print("=" * 50)
    
    tests = [
        ("直接 Webhook 測試", test_direct_webhook),
        ("直接 Bot 測試", test_direct_bot),
        ("我們的 Notifier 測試", test_our_notifier),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 執行時發生錯誤: {e}")
            results.append((test_name, False))
    
    # 總結
    print("\n" + "=" * 50)
    print("📊 測試結果總結")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{total} 項測試成功")
    
    if passed == total:
        print("🎉 恭喜！所有測試都成功！")
    else:
        print("⚠️  部分測試失敗，請檢查錯誤訊息。")
    
    return passed == total

if __name__ == "__main__":
    main()
