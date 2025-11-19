# Studio-Roulette-Test API Curl Commands

本文檔包含 Studio-Roulette-Test 表的所有 API curl 命令。

## 環境配置

- **Base URL**: `https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test`
- **Environment**: CIT
- **Game Code**: `Studio-Roulette-Test`

## 1. 獲取 Access Token

首先需要獲取 access token 才能使用其他 API。

### Bash

```bash
TOKEN=$(curl -X POST "https://crystal-table.iki-cit.cc/v2/service/sessions" \
  -H "accept: application/json" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -d '{"gameCode": "Studio-Roulette-Test", "role": "sdp"}' \
  --insecure | jq -r '.data.token')
```

### Fish Shell

```fish
set TOKEN (curl -X POST "https://crystal-table.iki-cit.cc/v2/service/sessions" \
  -H "accept: application/json" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -d '{"gameCode": "Studio-Roulette-Test", "role": "sdp"}' \
  --insecure | jq -r '.data.token')
```

---

## 2. Start (開始新一輪)

開始一個新的遊戲回合。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/start" \
  -H "accept: application/json" \
  -H "Bearer: Bearer $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

**響應說明**：
- 返回 `roundId` 和 `betPeriod`
- `roundId` 需要保存用於後續的 deal 操作

---

## 3. Bet Stop (停止下注)

停止當前回合的下注。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/bet-stop" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

---

## 4. Deal (開牌/開獎)

發送遊戲結果。需要提供 `roundId` 和結果。

```bash
# 注意：需要先從 start 響應中獲取 roundId
# result 格式為三個骰子的值，例如：[1, 2, 3]

curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/deal" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "timecode: $(date +%s)000" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "roundId": "YOUR_ROUND_ID",
    "sicBo": [1, 2, 3]
  }' \
  --insecure
```

**參數說明**：
- `roundId`: 從 start 響應中獲取的回合 ID
- `sicBo`: 三個骰子的結果，例如 `[1, 2, 3]`
- `timecode`: 當前時間戳（毫秒），可以使用 `$(date +%s)000` 生成

---

## 5. Finish (結束回合)

結束當前遊戲回合。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/finish" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

---

## 6. Pause (暫停)

暫停當前遊戲回合。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/pause" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "reason": "Test pause for Studio-Roulette-Test table"
  }' \
  --insecure
```

**參數說明**：
- `reason`: 暫停原因（字串）

---

## 7. Resume (恢復)

恢復暫停的遊戲回合。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/resume" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

---

## 8. Cancel (取消)

取消當前遊戲回合。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/cancel" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

---

## 9. Broadcast (廣播訊息)

發送廣播訊息給玩家。

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/broadcast" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "msgId": "SICBO_INVALID_AFTER_RESHAKE",
    "content": "Sicbo invalid result after reshake",
    "metadata": {
      "title": "SICBO RESHAKE",
      "description": "Invalid result detected, reshaking dice",
      "code": "SBE.1",
      "suggestion": "Dice will be reshaken shortly",
      "signalType": "warning",
      "audience": "players",
      "afterSeconds": 20
    }
  }' \
  --insecure
```

**參數說明**：
- `msgId`: 訊息 ID，常見值：
  - `SICBO_INVALID_AFTER_RESHAKE`: 重新搖骰後無效結果
  - `SICBO_INVALID_RESULT`: 無效結果
  - `SICBO_NO_SHAKE`: 未搖骰
- `content`: 訊息內容
- `metadata`: 元數據
  - `title`: 標題
  - `description`: 描述
  - `code`: 錯誤代碼
  - `suggestion`: 建議
  - `signalType`: 信號類型（`warning` 或 `error`）
  - `audience`: 目標受眾（預設：`players`）
  - `afterSeconds`: 延遲秒數（預設：20）

**常見 Broadcast 類型範例**：

### dice.reshake / dice.reroll / sicbo.reshake

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/broadcast" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "msgId": "SICBO_INVALID_AFTER_RESHAKE",
    "content": "Sicbo invalid result after reshake",
    "metadata": {
      "title": "SICBO RESHAKE",
      "description": "Invalid result detected, reshaking dice",
      "code": "SBE.1",
      "suggestion": "Dice will be reshaken shortly",
      "signalType": "warning",
      "audience": "players",
      "afterSeconds": 20
    }
  }' \
  --insecure
```

### sicbo.invalid_result

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/broadcast" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "msgId": "SICBO_INVALID_RESULT",
    "content": "Sicbo invalid result error",
    "metadata": {
      "title": "SICBO INVALID RESULT",
      "description": "Invalid result detected",
      "code": "SBE.2",
      "suggestion": "Please check the result",
      "signalType": "warning",
      "audience": "players",
      "afterSeconds": 20
    }
  }' \
  --insecure
```

### dice.no_shake / sicbo.no_shake

```bash
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/broadcast" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{
    "msgId": "SICBO_NO_SHAKE",
    "content": "Sicbo no shake error",
    "metadata": {
      "title": "SICBO NO SHAKE",
      "description": "Dice shaker did not shake",
      "code": "SBE.3",
      "suggestion": "Check the shaker mechanism",
      "signalType": "warning",
      "audience": "players",
      "afterSeconds": 20
    }
  }' \
  --insecure
```

---

## 完整遊戲流程範例

以下是一個完整的遊戲流程範例（Bash）：

```bash
#!/bin/bash

# 1. 獲取 Token
TOKEN=$(curl -X POST "https://crystal-table.iki-cit.cc/v2/service/sessions" \
  -H "accept: application/json" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -d '{"gameCode": "Studio-Roulette-Test", "role": "sdp"}' \
  --insecure | jq -r '.data.token')

echo "Token: $TOKEN"

# 2. 開始新回合
RESPONSE=$(curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/start" \
  -H "accept: application/json" \
  -H "Bearer: Bearer $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure)

ROUND_ID=$(echo $RESPONSE | jq -r '.data.table.tableRound.roundId')
echo "Round ID: $ROUND_ID"

# 3. 等待下注期（實際應用中需要等待）
sleep 10

# 4. 停止下注
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/bet-stop" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure

# 5. 發送結果
TIMECODE=$(date +%s)000
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/deal" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "timecode: $TIMECODE" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d "{
    \"roundId\": \"$ROUND_ID\",
    \"sicBo\": [1, 2, 3]
  }" \
  --insecure

# 6. 結束回合
curl -X POST "https://crystal-table.iki-cit.cc/v2/service/tables/Studio-Roulette-Test/finish" \
  -H "accept: application/json" \
  -H "Bearer: $TOKEN" \
  -H "x-signature: los-local-signature" \
  -H "Content-Type: application/json" \
  -H "Cookie: accessToken=$TOKEN" \
  -H "Connection: close" \
  -d '{}' \
  --insecure
```

---

## 注意事項

1. **Token 有效期**：Access token 可能會有過期時間，如果請求失敗，需要重新獲取 token。

2. **Bearer Header 格式**：
   - `start` API 使用 `Bearer: Bearer $TOKEN`（雙重 Bearer）
   - 其他 API 使用 `Bearer: $TOKEN`

3. **SSL 驗證**：所有命令都使用 `--insecure` 參數，這會跳過 SSL 證書驗證（對應 Python 中的 `verify=False`）。

4. **Cookie Header**：所有 API 都需要在 Cookie header 中提供 `accessToken`。

5. **Deal API 的 timecode**：`deal` API 需要提供 `timecode` header，值為當前時間戳（毫秒）。

6. **Round ID**：`deal` API 需要從 `start` API 的響應中獲取 `roundId`。

---

## 參考資料

- API 實現：`table_api/sb/api_v2_cit_sb.py`
- 測試腳本：
  - `test_studio-roulette-test_pause.py`
  - `test_studio-roulette-test_resume.py`
  - `test_studio-roulette-test_cancel.py`

