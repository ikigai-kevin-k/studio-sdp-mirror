# SDP Roulette WebSocket System

這個系統實現了一個基於 WebSocket 的輪盤系統，當一個 SDP 進入 idle state 時，會自動激活下一個可用的 SDP。

## 系統架構

- **ws_server.py**: WebSocket 伺服器，處理客戶端連線和訊息轉發
- **sdp-ARO-001-1.py**: 第一個 SDP 客戶端，發送 "roulette is down" 訊息
- **sdp-ARO-001-2.py**: 第二個 SDP 客戶端，接收激活通知

## 工作流程

1. **啟動伺服器**: 執行 `ws_server.py`
2. **啟動 SDP-ARO-001-2**: 執行 `sdp-ARO-001-2.py` (進入 idle state)
3. **啟動 SDP-ARO-001-1**: 執行 `sdp-ARO-001-1.py`
4. **觸發輪盤**: SDP-ARO-001-1 發送 "roulette is down" 訊息
5. **自動激活**: 伺服器自動通知 SDP-ARO-001-2 從 idle 轉換為 up state

## 安裝依賴

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 啟動 WebSocket 伺服器

```bash
python ws_server.py
```

伺服器將在 `ws://localhost:8765` 上運行。

### 2. 啟動 SDP-ARO-001-2 (等待激活)

```bash
python sdp-ARO-001-2.py
```

這個客戶端會連接到伺服器並進入 idle state，等待激活通知。

### 3. 啟動 SDP-ARO-001-1 (觸發輪盤)

```bash
python sdp-ARO-001-1.py
```

這個客戶端會連接到伺服器，等待 2 秒後自動發送 "roulette is down" 訊息，然後進入 idle state。

### 4. 自動激活流程

當 SDP-ARO-001-1 發送 "roulette is down" 訊息後：
- 伺服器會將 SDP-ARO-001-1 的狀態設為 idle
- 伺服器會自動找到下一個可用的客戶端 (SDP-ARO-001-2)
- 伺服器會發送激活訊息給 SDP-ARO-001-2
- SDP-ARO-001-2 會從 idle state 轉換為 up state

## 訊息格式

### 客戶端識別
```json
{
    "client_id": "ARO-001-1"
}
```

### 輪盤停止訊息
```json
{
    "type": "roulette_down",
    "client_id": "ARO-001-1",
    "message": "ARO-001-1 roulette is down",
    "timestamp": 1234567890.123
}
```

### 激活訊息
```json
{
    "type": "activate",
    "message": "Activating ARO-001-2 from idle to up state"
}
```

### 狀態變更通知
```json
{
    "type": "state_change_notification",
    "client_id": "ARO-001-1",
    "new_state": "idle",
    "timestamp": 1234567890.123
}
```

## 注意事項

- 確保按順序啟動：先啟動伺服器，再啟動客戶端
- 系統使用 round-robin 方式選擇下一個要激活的客戶端
- 所有客戶端都會收到狀態變更通知
- 使用 Ctrl+C 可以優雅地停止客戶端和伺服器
