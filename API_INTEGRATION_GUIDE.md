# API 整合指南

本文件說明 Studio SDP Roulette 系統中三種主要的 API 整合機制：
1. StudioAPI WebSocket Error Signal
2. TableAPI API Post
3. Slack Notification

---

## 1. StudioAPI WebSocket Error Signal

### 概述

StudioAPI WebSocket Error Signal 用於向 StudioAPI 服務器發送錯誤信號，通知系統發生異常情況。這些信號會通過 WebSocket 連接發送到指定的 table 和 device。

### 機制說明

- **連接方式**: WebSocket (wss://)
- **連接格式**: `wss://studio-api.iki-cit.cc/v1/ws?id={device_id}&token={token}`
- **消息格式**: JSON 格式的 exception event
- **信號類型**: `warn` (第一次) 或 `error` (第二次)

### 錯誤類型

系統支援多種錯誤類型，定義在 `ErrorMsgId` enum 中：

#### Roulette 錯誤
- `ROULETTE_SENSOR_STUCK` - 感應器卡住
- `ROUELTTE_WRONG_BALL_DIR` - 球方向錯誤
- `ROULETTE_LAUNCH_FAIL` - 發球失敗
- `ROULETTE_NO_BALL_DETECT` - 未檢測到球
- `ROULETTE_NO_WIN_NUM` - 未檢測到獲勝號碼
- `ROULETTE_NO_REACH_POS` - 未到達位置
- `ROULETTE_INVALID_AFTER_RELAUNCH` - 重新發球後無效
- `ROULETTE_WRONG_WHEEL_DIR` - 輪盤方向錯誤
- `ROULETTE_ENCODER_FAIL` - 編碼器故障
- `ROULETTE_BALL_DROP_FAIL` - 球掉落失敗
- `ROULETTE_COMPRESSOR_LEAK` - 壓縮機洩漏
- `ROULETTE_STUCK_NMB` - 號碼卡住

#### Service 錯誤
- `STREAM_DOWN` - 串流服務中斷
- `IDP_DOWN` - IDP 服務中斷
- `SDP_DOWN` - SDP 服務中斷
- `ROULETTE_DOWN` - 輪盤服務中斷

### 使用方式

#### 基本用法

```python
from studio_api.ws_err_sig import send_roulette_sensor_stuck_error
import asyncio

# 發送感應器卡住錯誤信號
async def send_error():
    success = await send_roulette_sensor_stuck_error(
        table_id="ARO-001",
        device_id="ARO-001-2",
        signal_type="warn"  # 或 "error"
    )
    return success

# 執行
result = asyncio.run(send_error())
```

#### 在 main_speed.py 中的使用

```python
from studio_api.ws_err_sig import send_roulette_sensor_stuck_error, send_roulette_wrong_ball_dir_error

def send_websocket_error_signal():
    """Send WebSocket error signal for Speed Roulette table"""
    def send_ws_error():
        try:
            result = asyncio.run(send_roulette_sensor_stuck_error(
                table_id=DETECTED_TABLE_ID,
                device_id=DETECTED_DEVICE_ID
            ))
            return result
        except Exception as e:
            print(f"Failed to send WebSocket error signal: {e}")
            return False
    
    # 在獨立線程中執行
    ws_thread = threading.Thread(target=send_ws_error)
    ws_thread.daemon = True
    ws_thread.start()
    ws_thread.join(timeout=10)
```

### 錯誤信號格式

```json
{
  "event": "exception",
  "data": {
    "signal": {
      "msgId": "ROULETTE_SENSOR_STUCK",
      "content": "Sensor broken causes roulette machine idle",
      "metadata": {
        "title": "SENSOR STUCK",
        "description": "Sensor broken causes roulette machine idle",
        "code": "ARE.3",
        "suggestion": "Clean or replace the ball",
        "signalType": "warn"
      }
    },
    "cmd": {}
  }
}
```

### 配置

配置文件: `conf/ws.json`

```json
{
  "server_url": "wss://studio-api.iki-cit.cc/v1/ws",
  "token": "0000",
  "tables": [
    {
      "table_id": "ARO-001",
      "name": "ARO-001",
      "device_id": "ARO-001-1"
    }
  ],
  "device_mapping": {
    "ARO-001-1": {
      "table_id": "ARO-001",
      "device_id": "ARO-001-1"
    },
    "ARO-001-2": {
      "table_id": "ARO-001",
      "device_id": "ARO-001-2"
    }
  }
}
```

### 範例：發送錯誤信號

```python
# 發送感應器卡住錯誤
await send_roulette_sensor_stuck_error(
    table_id="ARO-001",
    device_id="ARO-001-2",
    signal_type="warn"
)

# 發送球方向錯誤
await send_roulette_wrong_ball_dir_error(
    table_id="ARO-001",
    device_id="ARO-001-2",
    signal_type="warn"
)
```

---

## 2. TableAPI API Post

### 概述

TableAPI 用於與 LOS (Live Operations System) 進行通信，管理遊戲回合的生命週期。支援多個環境（CIT, UAT, PRD, STG, QAT, GLC）。

### API 端點類型

#### 1. Start Post - 開始新回合

開始一個新的遊戲回合，返回 `round_id` 和 `bet_period`。

**端點**: `POST {post_url}/start`

**請求格式**:
```python
def start_post_v2(url, token):
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
    }
    data = {}
    response = requests.post(f"{url}/start", headers=headers, json=data, verify=False)
    # 返回 (round_id, bet_period)
```

**回應格式**:
```json
{
  "data": {
    "table": {
      "tableRound": {
        "roundId": "123456"
      },
      "betPeriod": 20
    }
  }
}
```

#### 2. Deal Post - 發送結果

發送遊戲結果（獲勝號碼）。

**端點**: `POST {post_url}/deal`

**請求格式**:
```python
def deal_post_v2(url, token, round_id, result):
    timecode = str(int(time.time() * 1000))
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "timecode": timecode,
        "Cookie": f"accessToken={accessToken}",
    }
    data = {
        "roundId": f"{round_id}",
        "roulette": result,  # 獲勝號碼，例如 "0" 到 "36"
    }
    response = requests.post(f"{url}/deal", headers=headers, json=data, verify=False)
```

#### 3. Finish Post - 結束回合

結束當前遊戲回合。

**端點**: `POST {post_url}/finish`

**請求格式**:
```python
def finish_post_v2(url, token):
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
    }
    data = {}
    response = requests.post(f"{url}/finish", headers=headers, json=data, verify=False)
```

#### 4. Bet Stop Post - 停止下注

停止當前回合的下注階段。

**端點**: `POST {post_url}/betStop`

**請求格式**:
```python
def bet_stop_post(url, token):
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
    }
    data = {}
    response = requests.post(f"{url}/betStop", headers=headers, json=data, verify=False)
```

#### 5. Broadcast Post - 廣播通知

向玩家或 SDP 發送廣播通知（例如重新發球通知）。

**端點**: `POST {post_url}/broadcast`

**請求格式**:
```python
def broadcast_post_v2(url, token, broadcast_type, audience="players", afterSeconds=20):
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
    }
    data = {
        "broadcastType": broadcast_type,  # 例如 "roulette.relaunch"
        "audience": audience,  # "players" 或 "sdp"
        "afterSeconds": afterSeconds
    }
    response = requests.post(f"{url}/broadcast", headers=headers, json=data, verify=False)
```

### 環境支援

系統支援多個環境，每個環境有對應的 API 函數：

- **CIT**: `start_post_v2`, `deal_post_v2`, `finish_post_v2`, `broadcast_post_v2`
- **UAT**: `start_post_v2_uat`, `deal_post_v2_uat`, `finish_post_v2_uat`, `broadcast_post_v2_uat`
- **PRD**: `start_post_v2_prd`, `deal_post_v2_prd`, `finish_post_v2_prd`, `broadcast_post_v2_prd`
- **STG**: `start_post_v2_stg`, `deal_post_v2_stg`, `finish_post_v2_stg`, `broadcast_post_v2_stg`
- **QAT**: `start_post_v2_qat`, `deal_post_v2_qat`, `finish_post_v2_qat`, `broadcast_post_v2_qat`
- **GLC**: `start_post_v2_glc`, `deal_post_v2_glc`, `finish_post_v2_glc`, `broadcast_post_v2_glc`

### 在 main_speed.py 中的使用

```python
from table_api.sr.api_v2_sr import start_post_v2, deal_post_v2, finish_post_v2, broadcast_post_v2
from networkChecker import networkChecker

async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
    """重試函數，包含網絡錯誤檢查"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            return await func(*args) if asyncio.iscoroutinefunction(func) else func(*args)
        except (ConnectionError, urllib3.exceptions.NewConnectionError) as e:
            is_network_error, error_message = networkChecker(e)
            if is_network_error:
                await asyncio.sleep(retry_delay)
                retry_count += 1
                continue
            raise
    raise Exception(f"Max retries ({max_retries}) reached")

# 開始回合
async def _execute_start_post_async(table, token):
    post_url = f"{table['post_url']}{table['game_code']}"
    if table["name"] == "CIT":
        round_id, bet_period = await retry_with_network_check(
            start_post_v2, post_url, token
        )
    # ... 其他環境
    return table, round_id, bet_period

# 發送結果
async def _execute_deal_post_async(table, token, win_num):
    post_url = f"{table['post_url']}{table['game_code']}"
    if table["name"] == "CIT":
        await retry_with_network_check(
            deal_post_v2, post_url, token, table["round_id"], str(win_num)
        )
    # ... 其他環境

# 結束回合
async def _execute_finish_post_async(table, token):
    post_url = f"{table['post_url']}{table['game_code']}"
    if table["name"] == "CIT":
        await retry_with_network_check(finish_post_v2, post_url, token)
    # ... 其他環境
```

### 配置

配置文件: `conf/sr-1.json`

```json
[
  {
    "name": "PRD",
    "get_url": "https://crystal-table.ikg-game.cc/v2/service/tables/",
    "post_url": "https://crystal-table.ikg-game.cc/v2/service/tables/",
    "game_code": "ARO-001",
    "access_token": "eyJhbGci...",
    "table_token": "E5LN4END9Q"
  }
]
```

### 完整遊戲流程範例

```python
# 1. 開始新回合
round_id, bet_period = start_post_v2(post_url, token)
print(f"Round started: {round_id}, Bet period: {bet_period}")

# 2. 等待下注時間
time.sleep(bet_period)

# 3. 停止下注
bet_stop_post(post_url, token)

# 4. 發送結果
win_number = "0"  # 獲勝號碼
deal_post_v2(post_url, token, round_id, win_number)

# 5. 結束回合
finish_post_v2(post_url, token)
```

---

## 3. Slack Notification

### 概述

Slack Notification 用於向 Slack 頻道發送錯誤通知和狀態更新。支援多種發送方式：Webhook、Bot Token、User Token。

### 通知類型

#### 1. Roulette Sensor Error Notification

專門用於輪盤感應器錯誤的通知格式。

**使用方式**:
```python
from slack.slack_notifier import send_roulette_sensor_error_to_slack

success = send_roulette_sensor_error_to_slack(
    action_message="relaunch the wheel controller with *P 1",
    table_name="ARO-001-2 (speed - backup)",
    error_code="SENSOR_STUCK",
    mention_user="Mark Bochkov",
    channel="#alert-studio"
)
```

**參數說明**:
- `action_message`: 需要執行的操作訊息
- `table_name`: 桌台名稱（包含 device ID 和 alias）
- `error_code`: 錯誤代碼
- `mention_user`: 要 @ 提及的用戶名稱
- `channel`: 目標頻道

#### 2. General Error Notification

通用錯誤通知格式。

**使用方式**:
```python
from slack import send_error_to_slack

success = send_error_to_slack(
    error_message="Error description",
    error_code="ERROR_CODE",
    table_name="Table Name",
    environment="PRD",
    mention_user="Kevin Kuo",
    channel="#ge-studio"
)
```

### 發送方式

#### 1. Webhook (簡單訊息)

使用 Slack Webhook URL 發送簡單訊息。

```python
from slack.slack_notifier import SlackNotifier

notifier = SlackNotifier(
    webhook_url="https://hooks.slack.com/services/...",
    default_channel="#general"
)

success = notifier.send_simple_message("Hello from SDP!")
```

#### 2. Bot Token (豐富訊息)

使用 Bot Token 發送格式化的豐富訊息（支援 Blocks）。

```python
notifier = SlackNotifier(
    bot_token="xoxb-...",
    default_channel="#alert-studio"
)

success = notifier.send_roulette_sensor_error_notification(
    action_message="relaunch the wheel controller",
    table_name="ARO-001-2 (speed - backup)",
    error_code="SENSOR_STUCK",
    mention_user="Mark Bochkov",
    channel="#alert-studio"
)
```

#### 3. User Token (可刪除訊息)

使用 User Token 發送的訊息可以被刪除。

```python
notifier = SlackNotifier(
    user_token="xoxp-...",
    default_channel="#ge-studio"
)
```

### 頻道配置

不同類型的錯誤發送到不同的頻道：

- **Sensor Errors**: `#alert-studio` (提及 Mark Bochkov)
- **Auto-recoverable Errors**: `#ge-studio` (提及 Kevin Kuo)
- **General Errors**: `#studio-rnd` (預設)

### 在 main_speed.py 中的使用

```python
from slack.slack_notifier import send_roulette_sensor_error_to_slack

def send_sensor_error_to_slack():
    """Send sensor error notification to Slack"""
    global sensor_error_sent, current_mode
    
    # 跳過 idle mode 的錯誤處理
    with mode_lock:
        if current_mode == "idle":
            return False
    
    if sensor_error_sent:
        return False
    
    try:
        success = send_roulette_sensor_error_to_slack(
            action_message="relaunch the wheel controller with *P 1",
            table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
            error_code="SENSOR_STUCK",
            mention_user="Mark Bochkov",
            channel="#alert-studio"
        )
        
        if success:
            sensor_error_sent = True
            return True
        return False
    except Exception as e:
        print(f"Error sending sensor error notification: {e}")
        return False
```

### 錯誤代碼對應

| Error Code | 說明 | 頻道 | 提及用戶 |
|------------|------|------|----------|
| `SENSOR_STUCK` | 感應器卡住 | `#alert-studio` | Mark Bochkov |
| `ROUELTTE_WRONG_BALL_DIR` | 球方向錯誤 | `#ge-studio` | Kevin Kuo |
| `ROULETTE_LAUNCH_FAIL` | 發球失敗 | `#ge-studio` | Kevin Kuo |
| `ROULETTE_RELAUNCH_FAILED` | 重新發球失敗 | `#ge-studio` | Kevin Kuo |

### 訊息格式範例

#### Roulette Sensor Error 格式

```
🚨 Roulette Error
@Mark Bochkov Error requires your attention

Table: ARO-001-2 (speed - backup)
Error Code: SENSOR_STUCK
Action:
relaunch the wheel controller with *P 1

Time: 2025-11-18 12:51:30
```

### 配置

環境變數配置 (`.env` 或系統環境變數):

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_BOT_TOKEN=xoxb-...
SLACK_USER_TOKEN=xoxp-...
SLACK_DEFAULT_CHANNEL=#studio-rnd
```

### 防重複機制

系統會自動防止在 30 秒內發送重複的訊息：

```python
# 自動檢查訊息是否在最近 30 秒內已發送
# 使用訊息內容的 hash 值來判斷
```

---

## 整合範例

### 完整錯誤處理流程

```python
# 1. 檢測到錯誤（例如感應器卡住）
if sensor_error_detected:
    # 2. 發送 WebSocket 錯誤信號
    def send_ws_error():
        asyncio.run(send_roulette_sensor_stuck_error(
            table_id=DETECTED_TABLE_ID,
            device_id=DETECTED_DEVICE_ID,
            signal_type="warn"
        ))
    
    threading.Thread(target=send_ws_error).start()
    
    # 3. 發送 Slack 通知
    send_roulette_sensor_error_to_slack(
        action_message="relaunch the wheel controller with *P 1",
        table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
        error_code="SENSOR_STUCK",
        mention_user="Mark Bochkov",
        channel="#alert-studio"
    )
    
    # 4. 發送廣播通知（如果需要）
    execute_broadcast_post(
        table,
        token,
        broadcast_type="roulette.relaunch"
    )
```

### 遊戲流程整合

```python
# 1. 開始新回合
table, round_id, bet_period = execute_start_post(table, token)

# 2. 等待下注時間
time.sleep(bet_period)

# 3. 停止下注
bet_stop_post(post_url, token)

# 4. 檢測獲勝號碼
win_number = detect_winning_number()

# 5. 發送結果
execute_deal_post(table, token, win_number)

# 6. 結束回合
execute_finish_post(table, token)
```

---

## 最佳實踐

### 1. 錯誤處理

- 所有 API 調用都應該使用 `retry_with_network_check` 包裝
- 實現適當的重試機制和超時處理
- 記錄所有錯誤以便追蹤

### 2. 環境檢測

- 使用 `env_detect.py` 自動檢測環境
- 根據 hostname 自動識別 table code 和 device ID
- 使用動態的 device alias (main/backup)

### 3. 通知策略

- Sensor errors 發送到 `#alert-studio` 並提及 Mark Bochkov
- Auto-recoverable errors 發送到 `#ge-studio` 並提及 Kevin Kuo
- 使用防重複機制避免訊息轟炸

### 4. 模式管理

- 在 `idle` mode 時跳過錯誤處理和 API 調用
- 使用 `mode_lock` 確保線程安全

---

## 參考資料

- StudioAPI WebSocket 文檔: `studio_api/ws_err_sig.py`
- TableAPI 文檔: `table_api/sr/api_v2_sr.py`
- Slack Notification 文檔: `slack/slack_notifier.py`
- 環境檢測: `env_detect.py`

