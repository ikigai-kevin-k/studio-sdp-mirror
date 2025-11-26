# Mock StudioAPI Server

## 概述

`mock_studio_api_server.py` 是一個模擬 StudioAPI WebSocket 伺服器的測試工具，用於測試 `main_speed.py` 在接收到 SDP down 訊號時從 running mode 切換到 idle mode 的功能。

## 功能特性

1. **WebSocket 伺服器**：模擬 StudioAPI 的 WebSocket 伺服器
2. **連接管理**：追蹤和管理多個客戶端連接
3. **SDP Down 訊號發送**：支援發送 SDP down 訊號給連接的客戶端
4. **多種訊號格式**：支援 main_speed.py 能識別的多種訊號格式
5. **易於擴充**：設計時考慮了未來替換成真實 StudioAPI 伺服器的需求

## 安裝需求

```bash
pip install websockets
```

## 使用方法

### 1. 啟動 Mock Server

#### 基本啟動
```bash
cd /home/rnd/studio-sdp-roulette
python tests/mock_studio_api_server.py
```

#### 自訂端口和主機
```bash
python tests/mock_studio_api_server.py --host 0.0.0.0 --port 8080
```

#### 互動模式
```bash
python tests/mock_studio_api_server.py --interactive
```

在互動模式下，可以使用以下命令：
- `list` - 列出所有連接的客戶端
- `send <table_id> [device_name]` - 發送 SDP down 訊號給指定客戶端
- `send-all` - 發送 SDP down 訊號給所有客戶端
- `quit` - 退出互動模式

### 2. 配置 main_speed.py 連接到 Mock Server

修改 `conf/ws.json` 中的 `server_url`：

```json
{
    "server_url": "ws://localhost:8080/v1/ws",
    "token": "0000"
}
```

### 3. 發送 SDP Down 訊號

#### 方法 1：使用 CLI 參數
```bash
# 啟動 server 並自動發送訊號
python tests/mock_studio_api_server.py --send-sdp-down --table-id ARO-001 --device-name ARO-001-1
```

#### 方法 2：使用互動模式
```bash
python tests/mock_studio_api_server.py --interactive
# 然後輸入: send ARO-001 ARO-001-1
```

#### 方法 3：在 Python 程式中使用
```python
import asyncio
from tests.mock_studio_api_server import MockStudioAPIServer, send_sdp_down

async def test():
    server = MockStudioAPIServer(host="localhost", port=8080)
    # 啟動 server (在背景執行)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(2)  # 等待客戶端連接
    
    # 發送 SDP down 訊號
    await server.send_sdp_down_signal(
        table_id="ARO-001",
        device_name="ARO-001-1"
    )

asyncio.run(test())
```

## 訊號格式

Mock server 支援以下訊號格式（main_speed.py 都能識別）：

### 格式 1：簡單格式（預設）
```json
{
  "sdp": "down"
}
```

### 格式 2：嵌套格式（使用 send_sdp_down_signal_alternative_format）
```json
{
  "signal": {
    "msgId": "SDP_DOWN",
    "content": "DOWN",
    "device": "sdp",
    "status": "down"
  }
}
```

## 測試流程

1. **啟動 Mock Server**
   ```bash
   python tests/mock_studio_api_server.py --interactive
   ```

2. **啟動 main_speed.py**
   ```bash
   python main_speed.py
   ```

3. **確認連接**
   在 mock server 的互動模式中輸入 `list`，應該能看到 main_speed.py 的連接。

4. **發送 SDP Down 訊號**
   在互動模式中輸入：
   ```
   send ARO-001 ARO-001-1
   ```

5. **驗證行為**
   檢查 main_speed.py 的日誌，應該能看到：
   - 收到 "down" 訊號
   - Mode 從 "running" 切換到 "idle"
   - 觸發 idle mode 的處理邏輯

## 切換到真實 StudioAPI Server

當需要切換到真實的 StudioAPI server 時：

1. **修改配置**
   在 `conf/ws.json` 中將 `server_url` 改回真實伺服器：
   ```json
   {
       "server_url": "wss://studio-api.iki-cit.cc/v1/ws",
       "token": "YOUR_TOKEN"
   }
   ```

2. **保持兼容性**
   Mock server 的訊號格式與真實 StudioAPI server 的格式兼容，所以不需要修改 main_speed.py 的程式碼。

## 架構設計

### 擴充性考量

1. **配置驅動**：使用 JSON 配置文件管理 mock/real server 切換
2. **介面兼容**：Mock server 的 WebSocket 介面與真實 server 兼容
3. **訊號格式標準化**：使用標準的 JSON 格式，易於擴充

### 未來整合

當整合真實 StudioAPI server 時：
- 保持相同的 WebSocket 連接格式
- 保持相同的訊號格式
- 可以通過配置或環境變數切換

## 疑難排解

### 問題：客戶端無法連接

**解決方案**：
1. 確認 mock server 正在運行
2. 檢查端口是否被占用：`netstat -an | grep 8080`
3. 確認 `conf/ws.json` 中的 `server_url` 指向 mock server

### 問題：訊號發送後沒有反應

**解決方案**：
1. 確認客戶端已連接（使用 `list` 命令）
2. 檢查 main_speed.py 的日誌
3. 確認訊號格式正確

### 問題：多個客戶端連接

**解決方案**：
- 使用 `--table-id` 和 `--device-name` 參數精確指定目標客戶端
- 在互動模式中使用 `send <table_id> <device_name>` 指定目標

## 範例腳本

創建 `tests/test_sdp_down_signal.py` 來測試：

```python
#!/usr/bin/env python3
"""Test script for sending SDP down signal."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tests.mock_studio_api_server import MockStudioAPIServer

async def test_sdp_down():
    """Test sending SDP down signal."""
    server = MockStudioAPIServer(host="localhost", port=8080)
    
    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(2)  # Wait for clients
    
    # List clients
    clients = server.list_connected_clients()
    print(f"Connected clients: {clients}")
    
    # Send SDP down signal
    await server.send_sdp_down_signal(
        table_id="ARO-001",
        device_name="ARO-001-1"
    )
    
    await asyncio.sleep(1)
    await server.stop()

if __name__ == "__main__":
    asyncio.run(test_sdp_down())
```

## 注意事項

1. **端口衝突**：確保 mock server 使用的端口沒有被其他服務占用
2. **連接順序**：建議先啟動 mock server，再啟動 main_speed.py
3. **測試環境**：建議在開發/測試環境中使用，不要用於生產環境

