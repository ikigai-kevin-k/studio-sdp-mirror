# 手動邀請 Bot 到私有頻道指南

## 問題說明

即使添加了 `groups:read` 權限，私有頻道（如 `studio-rnd`）在 bot 被邀請加入之前，不會出現在 API 的頻道列表中。

## 解決方案：手動邀請 Bot

### 方法 1: 在 Slack Web/Desktop App 中邀請

1. **打開 Slack**（Web 或 Desktop App）
2. **進入 `#studio-rnd` 頻道**
3. **點擊頻道名稱**（在頂部）
4. **選擇 "Integrations" 或 "Apps" 標籤**
5. **點擊 "Add apps" 或 "Browse apps"**
6. **搜尋你的 Bot 名稱**（例如：SDP Bot）
7. **點擊 "Add" 或 "Install"**
8. **確認添加**

### 方法 2: 使用頻道設定

1. **進入 `#studio-rnd` 頻道**
2. **點擊頻道名稱** → **"Settings"**
3. **找到 "Integrations" 區段**
4. **點擊 "Add apps"**
5. **搜尋並添加你的 Bot**

### 方法 3: 使用頻道 ID 直接加入（如果知道 ID）

如果你知道 `studio-rnd` 的頻道 ID，可以直接使用腳本加入：

```bash
cd /home/rnd/studio-sdp-roulette
./slack/add_bot_by_channel_id.sh CHANNEL_ID
```

**如何獲取頻道 ID**：
- 打開 Slack Web App
- 進入 `#studio-rnd` 頻道
- 查看瀏覽器網址列：`https://workspace.slack.com/archives/CHANNEL_ID`
- 複製 `CHANNEL_ID` 部分

## 驗證 Bot 是否已加入

邀請後，可以再次執行腳本驗證：

```bash
./slack/get_channel_id.sh studio-rnd
```

如果成功，應該會看到：
```
✅ Found channel #studio-rnd
Channel ID: C1234567890
Is Private: true
```

## 注意事項

- 私有頻道需要 bot 被明確邀請才能看到
- 即使有 `groups:read` 權限，未加入的私有頻道不會出現在列表中
- 公開頻道（如 `ge-studio`）不需要邀請，bot 可以直接加入

