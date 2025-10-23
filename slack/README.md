# 🚀 Slack 通知功能包

這個目錄包含了 SDP Roulette 系統的完整 Slack 通知功能。

## 📁 目錄結構

```
slack/
├── __init__.py              # 包初始化文件
├── README.md                # 本文件
├── slack_notifier.py        # 主要的 Slack 通知模組
├── README_SLACK.md          # 詳細使用指南
├── SLACK_SETUP_GUIDE.md     # 完整設定指南
├── slack_usage_examples.py  # 使用範例
├── test_slack_setup.py      # 設定測試腳本
├── test_slack_message.py    # 訊息發送測試
├── debug_slack.py           # 診斷腳本
└── simple_slack_test.py     # 簡單測試腳本
```

## 🚀 快速開始

### 1. 導入功能

```python
# 方法 1: 從 slack 包導入
from slack import SlackNotifier, send_error_to_slack

# 方法 2: 直接導入模組
from slack.slack_notifier import SlackNotifier
```

### 2. 發送通知

```python
# 錯誤通知
send_error_to_slack(
    "Table round not finished yet",
    "STG",
    "BCR-001", 
    "13003"
)

# 成功通知
from slack import send_success_to_slack
send_success_to_slack(
    "Operation completed",
    "PRD",
    "BCR-001"
)
```

## 📚 詳細文檔

- **[README_SLACK.md](README_SLACK.md)** - 完整使用指南
- **[SLACK_SETUP_GUIDE.md](SLACK_SETUP_GUIDE.md)** - 設定指南
- **[slack_usage_examples.py](slack_usage_examples.py)** - 使用範例

## 🧪 測試

```bash
# 進入 slack 目錄
cd slack

# 執行完整測試
python3 test_slack_setup.py

# 執行訊息發送測試
python3 test_slack_message.py

# 執行診斷測試
python3 debug_slack.py
```

## 🔧 設定

確保你的 `.env` 文件包含必要的 Slack 憑證：

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_TOKEN=xoxp-your-user-token
```

## 📊 功能狀態

| 功能 | 狀態 | 備註 |
|------|------|------|
| 基本訊息發送 | ✅ 已驗證 | Webhook 模式 |
| 錯誤通知 | ✅ 已驗證 | 格式化訊息 |
| 成功通知 | ✅ 已驗證 | 格式化訊息 |
| 豐富格式訊息 | ✅ 已驗證 | Bot Token 模式 |
| 環境變數載入 | ✅ 已驗證 | 自動載入 .env |

## 🎯 版本信息

- **當前版本**: v1.4.0
- **狀態**: 生產就緒
- **最後更新**: 2024-08-22

## 📞 支援

如果遇到問題，請參考：
1. [README_SLACK.md](README_SLACK.md) - 詳細使用說明
2. [SLACK_SETUP_GUIDE.md](SLACK_SETUP_GUIDE.md) - 設定指南
3. 測試腳本 - 驗證功能正常運作

---

**🎉 恭喜！你的 Slack 通知功能已經完全就緒！**
