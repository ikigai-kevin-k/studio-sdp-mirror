#!/usr/bin/env python3
"""
簡單的 Slack 訊息測試腳本
測試實際發送訊息到 Slack
"""

from slack_notifier import (
    SlackNotifier, 
    send_error_to_slack, 
    send_success_to_slack
)

def test_simple_message():
    """測試發送簡單訊息"""
    print("🧪 測試發送簡單訊息...")
    
    notifier = SlackNotifier()
    success = notifier.send_simple_message("🎲 來自 SDP Roulette 的測試訊息！")
    
    if success:
        print("✅ 簡單訊息發送成功！")
    else:
        print("❌ 簡單訊息發送失敗！")
    
    return success

def test_error_notification():
    """測試發送錯誤通知"""
    print("\n🚨 測試發送錯誤通知...")
    
    success = send_error_to_slack(
        error_message="測試錯誤：Table round not finished yet",
        error_code="13003",
        table_name="BCR-001",
        environment="STG"
    )
    
    if success:
        print("✅ 錯誤通知發送成功！")
    else:
        print("❌ 錯誤通知發送失敗！")
    
    return success

def test_success_notification():
    """測試發送成功通知"""
    print("\n✅ 測試發送成功通知...")
    
    success = send_success_to_slack(
        message="測試成功：Table operation completed",
        environment="PRD",
        table_name="BCR-001"
    )
    
    if success:
        print("✅ 成功通知發送成功！")
    else:
        print("❌ 成功通知發送失敗！")
    
    return success

def test_rich_message():
    """測試發送豐富格式訊息"""
    print("\n🎨 測試發送豐富格式訊息...")
    
    notifier = SlackNotifier()
    
    # 創建豐富的訊息區塊
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🎯 SDP Roulette 系統狀態",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "這是一個測試訊息，展示豐富格式功能"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*狀態:*\n🟢 正常運行"
                },
                {
                    "type": "mrkdwn",
                    "text": "*環境:*\nSTG"
                }
            ]
        }
    ]
    
    success = notifier.send_rich_message(
        channel="#general",  # 使用 Bot Token 發送到指定頻道
        blocks=blocks,
        text="SDP Roulette 系統狀態更新"
    )
    
    if success:
        print("✅ 豐富格式訊息發送成功！")
    else:
        print("❌ 豐富格式訊息發送失敗！")
    
    return success

def main():
    """主測試函數"""
    print("🚀 Slack 訊息發送測試開始")
    print("=" * 50)
    
    tests = [
        ("簡單訊息測試", test_simple_message),
        ("錯誤通知測試", test_error_notification),
        ("成功通知測試", test_success_notification),
        ("豐富格式訊息測試", test_rich_message),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
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
        print("🎉 恭喜！所有訊息都成功發送到 Slack！")
        print("請檢查你的 Slack 頻道確認訊息是否收到。")
    else:
        print("⚠️  部分測試失敗，請檢查錯誤訊息。")
    
    return passed == total

if __name__ == "__main__":
    main()
