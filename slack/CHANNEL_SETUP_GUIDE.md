# Slack 頻道設定指南

本指南說明如何設定 Slack bot 以支援多頻道通知功能。

## 📋 功能說明

目前系統支援彈性頻道設定：
- **sensor_error** 通知：發送到 `#studio-rnd` 頻道
- **其他通知**：發送到 `#ge-studio` 頻道（預設）

## 🔧 Slack Bot 設定步驟

### 1. 確保 Bot 已加入所需頻道

Slack bot 必須先被邀請加入以下頻道：
- `#ge-studio` - 一般通知頻道
- `#studio-rnd` - Sensor 錯誤通知頻道

#### 方法 A: 在 Slack 中手動邀請（推薦，特別是私有頻道）

**⚠️ 重要：對於私有頻道（如 `studio-rnd`），必須先手動邀請 bot，API 才能看到該頻道**

**步驟 1: 邀請 Bot 到 `#ge-studio` 頻道**
1. 進入 `#ge-studio` 頻道
2. 點擊頻道名稱 → "Integrations" → "Add apps"
3. 搜尋並添加你的 Slack Bot（SDP Bot）
4. 確認添加

**步驟 2: 邀請 Bot 到 `#studio-rnd` 頻道**
1. 進入 `#studio-rnd` 頻道
2. 點擊頻道名稱 → "Integrations" → "Add apps"
3. 搜尋並添加你的 Slack Bot（SDP Bot）
4. 確認添加

**驗證 Bot 是否已加入**：
邀請後，可以執行以下命令驗證：
```bash
./slack/get_channel_id.sh studio-rnd
```

如果成功，應該會看到：
```
✅ Found channel #studio-rnd
Channel ID: C1234567890
Is Private: true
```

#### 方法 B: 使用 Bot Token API 加入頻道

**方法 B-1: 使用提供的腳本（推薦）**

我們提供了兩個便利腳本：

1. **獲取頻道 ID**：
```bash
cd /home/rnd/studio-sdp-roulette
./slack/get_channel_id.sh studio-rnd
```

2. **將 Bot 加入頻道**（自動獲取 ID 並加入）：
```bash
cd /home/rnd/studio-sdp-roulette
./slack/add_bot_to_channel.sh
```

**方法 B-2: 手動使用 curl**

**步驟 1: 獲取頻道 ID**

從 `.env` 文件讀取 token 並獲取頻道列表：
```bash
# 從 .env 讀取 SLACK_BOT_TOKEN
export $(cat .env | grep SLACK_BOT_TOKEN | xargs)

# 獲取所有頻道列表
curl -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" | jq '.channels[] | select(.name=="studio-rnd") | {name: .name, id: .id}'
```

如果沒有 `jq`，可以使用：
```bash
curl -s -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" | grep -A 5 '"name":"studio-rnd"'
```

**步驟 2: 將 Bot 加入頻道**

獲取 channel ID 後（例如：`C1234567890`），使用以下命令加入：
```bash
# 從 .env 讀取 SLACK_BOT_TOKEN
export $(cat .env | grep SLACK_BOT_TOKEN | xargs)

# 加入頻道（替換 CHANNEL_ID 為實際的頻道 ID）
curl -X POST https://slack.com/api/conversations.join \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID"}'
```

**一行命令範例**（如果已知 channel ID）：
```bash
curl -X POST https://slack.com/api/conversations.join \
  -H "Authorization: Bearer $(grep SLACK_BOT_TOKEN .env | cut -d'=' -f2)" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C1234567890"}'
```

#### 方法 C: 使用頻道 ID 直接加入（無需 groups:read 權限）

如果無法添加 `groups:read` 權限，可以使用頻道 ID 直接加入：

**步驟 1: 獲取頻道 ID**

有幾種方式可以獲取頻道 ID：

1. **從 Slack Web App URL**：
   - 打開 Slack Web App
   - 進入 `#studio-rnd` 頻道
   - 查看瀏覽器網址列，URL 格式為：`https://workspace.slack.com/archives/CHANNEL_ID`
   - 複製 `CHANNEL_ID` 部分（例如：`C1234567890`）

2. **從 Slack Desktop App**：
   - 右鍵點擊頻道名稱
   - 選擇 "View channel details" 或 "Copy link"
   - 從連結中提取 Channel ID

**步驟 2: 使用腳本加入頻道**

```bash
cd /home/rnd/studio-sdp-roulette
./slack/add_bot_by_channel_id.sh C1234567890
```

**步驟 3: 或使用 curl 手動加入**

```bash
# 從 .env 讀取 SLACK_BOT_TOKEN
export $(cat .env | grep SLACK_BOT_TOKEN | xargs)

# 加入頻道（替換為實際的頻道 ID）
curl -X POST https://slack.com/api/conversations.join \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C1234567890"}'
```

### 2. 檢查 Bot Token 權限

確保 Bot Token 具有以下權限（Scopes）：
- `chat:write` - 發送訊息
- `chat:write.public` - 在公開頻道發送訊息（如果頻道是公開的）
- `channels:read` - 讀取公開頻道資訊
- `groups:read` - **讀取私有頻道資訊（如果頻道是私有的，如 studio-rnd）** ⚠️ 重要
- `users:read` - 讀取使用者資訊（用於 @ mention 功能）

**⚠️ 重要：如果 `studio-rnd` 是私有頻道，必須添加 `groups:read` 權限**

**如何添加權限**：
1. 前往 https://api.slack.com/apps
2. 選擇你的 Slack App（SDP Bot）
3. 在左側選單點擊 "OAuth & Permissions"
4. 在 "Bot Token Scopes" 區段，點擊 "Add an OAuth Scope"
5. 添加 `groups:read` 權限
6. 點擊頁面頂部的 "Reinstall App" 按鈕
7. 確認重新安裝到 workspace

**如果無法添加 `groups:read` 權限**，可以使用頻道 ID 直接加入（見下方「方法 C」）

### 3. 環境變數設定

在 `.env` 文件中設定：

```bash
# Slack 憑證
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# 預設頻道（可選，預設為 #ge-studio）
SLACK_DEFAULT_CHANNEL=#ge-studio
```

## 📝 程式碼使用範例

### Sensor Error 通知（發送到 studio-rnd）

```python
from slack import send_error_to_slack

send_error_to_slack(
    error_message="Speed Roulette Sensor Error, please relaunch the wheel",
    error_code="SENSOR_STUCK",
    table_name="Speed Roulette",
    environment="PRD",
    mention_user="Kevin Kuo",
    channel="#studio-rnd",  # 指定發送到 studio-rnd
)
```

### 一般錯誤通知（發送到 ge-studio，預設）

```python
from slack import send_error_to_slack

send_error_to_slack(
    error_message="Roulette relaunch notification sent successfully",
    error_code="ROULETTE_RELAUNCH",
    table_name="ARO-001",
    environment="PRD",
    # 不指定 channel，會使用預設的 #ge-studio
)
```

### 使用 SlackNotifier 類別指定頻道

```python
from slack.slack_notifier import SlackNotifier

# 建立 notifier，指定預設頻道
notifier = SlackNotifier(default_channel="#ge-studio")

# 發送通知到預設頻道
notifier.send_error_notification(
    error_message="Error message",
    environment="PRD",
)

# 發送通知到指定頻道（覆蓋預設）
notifier.send_error_notification(
    error_message="Error message",
    environment="PRD",
    channel="#studio-rnd",  # 覆蓋預設頻道
)
```

## 🔍 頻道 ID vs 頻道名稱

Slack API 支援兩種頻道識別方式：

1. **頻道名稱**（推薦）：`#ge-studio`、`#studio-rnd`
   - 更易讀，不需要查找頻道 ID
   - 必須包含 `#` 前綴

2. **頻道 ID**：`C1234567890`
   - 更穩定，不會因頻道重新命名而改變
   - 需要透過 API 查詢

### 查詢頻道 ID

**使用提供的腳本（推薦）**：
```bash
cd /home/rnd/studio-sdp-roulette
./slack/get_channel_id.sh studio-rnd
```

**手動使用 curl**：
```bash
# 從 .env 讀取 token
export $(cat .env | grep SLACK_BOT_TOKEN | xargs)

# 獲取頻道列表並查找 studio-rnd
curl -s -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" | jq '.channels[] | select(.name=="studio-rnd") | {name: .name, id: .id, is_private: .is_private}'
```

**如果沒有 jq，使用 grep**：
```bash
curl -s -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" | grep -A 10 '"name":"studio-rnd"'
```

## ⚠️ 常見問題

### 問題 1: Bot 無法發送訊息到頻道

**症狀**：收到 `channel_not_found` 或 `not_in_channel` 錯誤

**解決方案**：
1. 確認 Bot 已被邀請加入該頻道
2. 確認頻道名稱正確（包含 `#` 前綴）
3. 確認 Bot Token 有 `chat:write` 和 `chat:write.public` 權限

### 問題 2: Bot 無法 @ mention 用戶

**症狀**：訊息發送成功但沒有 @ mention

**解決方案**：
1. 確認 Bot Token 有 `users:read` 權限
2. 確認用戶存在於 Slack workspace 中
3. 確認用戶顯示名稱正確（區分大小寫）

### 問題 3: 訊息發送到錯誤頻道

**症狀**：訊息沒有發送到預期的頻道

**解決方案**：
1. 檢查 `channel` 參數是否正確傳遞
2. 檢查環境變數 `SLACK_DEFAULT_CHANNEL` 是否設定正確
3. 確認頻道名稱格式正確（包含 `#` 前綴）

## 📚 相關文件

- [Slack API 文件](https://api.slack.com/)
- [Slack Bot Token Scopes](https://api.slack.com/scopes)
- [Slack 頻道管理](https://slack.com/help/articles/201402297-Create-a-channel)

## 🔄 更新記錄

- 2025-11-12: 新增多頻道支援功能
  - Sensor error 通知發送到 `#studio-rnd`
  - 其他通知發送到 `#ge-studio`（預設）

