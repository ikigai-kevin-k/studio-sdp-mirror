#!/usr/bin/env python3
"""
測試新的 Slack 包結構
"""

def test_package_import():
    """測試包導入"""
    print("🧪 測試 Slack 包導入...")
    
    try:
        from slack import SlackNotifier, send_error_to_slack, send_success_to_slack
        print("✅ 包導入成功")
        return True
    except ImportError as e:
        print(f"❌ 包導入失敗: {e}")
        return False

def test_direct_import():
    """測試直接模組導入"""
    print("\n🧪 測試直接模組導入...")
    
    try:
        from slack.slack_notifier import SlackNotifier
        print("✅ 直接模組導入成功")
        return True
    except ImportError as e:
        print(f"❌ 直接模組導入失敗: {e}")
        return False

def test_functionality():
    """測試功能"""
    print("\n🧪 測試功能...")
    
    try:
        from slack import send_error_to_slack
        
        # 測試發送錯誤通知
        success = send_error_to_slack(
            "測試錯誤：Package structure test",
            "TEST",
            "TEST-TABLE",
            "99999"
        )
        
        if success:
            print("✅ 功能測試成功")
            return True
        else:
            print("❌ 功能測試失敗")
            return False
            
    except Exception as e:
        print(f"❌ 功能測試錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 Slack 包結構測試")
    print("=" * 50)
    
    tests = [
        ("包導入測試", test_package_import),
        ("直接模組導入測試", test_direct_import),
        ("功能測試", test_functionality),
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
        print("🎉 恭喜！Slack 包結構完全正常！")
    else:
        print("⚠️  部分測試失敗，請檢查包結構。")
    
    return passed == total

if __name__ == "__main__":
    main()
