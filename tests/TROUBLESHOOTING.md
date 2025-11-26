# Mock Server 連接問題排查指南

## 問題：Mock Server 顯示 "No clients connected"

### 檢查清單

#### 1. 確認 Mock Server 正在運行

```bash
# 檢查端口是否被占用
netstat -an | grep 8081
# 或
lsof -i :8081
```

如果沒有輸出，表示 mock server 沒有運行。

#### 2. 確認配置正確

```bash
# 檢查配置
python tests/diagnose_connection.py
```

確認 `conf/ws.json` 中的 `server_url` 是：
```json
{
    "server_url": "ws://localhost:8081/v1/ws"
}
```

**重要**：使用 `ws://` 而不是 `wss://`（mock server 不使用 SSL）

#### 3. 確認 main_speed.py 正在運行

```bash
# 檢查 main_speed.py 進程
ps aux | grep main_speed.py
```

#### 4. 檢查 main_speed.py 的日誌

啟動 `main_speed.py` 時，應該看到：
```
[timestamp] Connected to StudioAPI WebSocket
StudioAPI >>> Connected to StudioAPI WebSocket
```

如果沒有看到這些訊息，表示連接失敗。

#### 5. 檢查 Mock Server 日誌

當 `main_speed.py` 嘗試連接時，mock server 應該顯示：
```
🔌 New connection attempt from 127.0.0.1:xxxxx
📋 Connection path: /v1/ws?token=0000&id=ARO-001&device=ARO-001-1
📋 Parsed query params: {'token': '0000', 'id': 'ARO-001', 'device': 'ARO-001-1'}
🔗 New connection: ARO-001-ARO-001-1 (table_id=ARO-001, device=ARO-001-1, token=0000)
```

如果沒有看到這些訊息，表示連接請求沒有到達 mock server。

### 常見問題和解決方案

#### 問題 1：配置指向錯誤的 server

**症狀**：`main_speed.py` 嘗試連接到真實 server 而不是 mock server

**解決**：
```bash
# 更新配置
cp conf/ws.json.mock conf/ws.json
# 或手動編輯 conf/ws.json，將 server_url 改為 ws://localhost:8081/v1/ws
```

#### 問題 2：端口不匹配

**症狀**：Mock server 運行在 8080，但配置指向 8081

**解決**：
```bash
# 選項 A：使用正確的端口啟動 mock server
python tests/mock_studio_api_server.py --port 8081

# 選項 B：更新配置指向正確的端口
# 編輯 conf/ws.json，將端口改為 8080
```

#### 問題 3：main_speed.py 沒有啟動 WebSocket 連接

**症狀**：`main_speed.py` 運行但沒有嘗試連接

**檢查**：
- 確認 `main_speed.py` 中有啟動 WebSocket 連接的代碼
- 檢查是否有錯誤訊息阻止了連接

#### 問題 4：連接被拒絕

**症狀**：Mock server 日誌顯示連接嘗試，但立即關閉

**可能原因**：
- Path 不匹配
- Query 參數格式錯誤
- 連接處理邏輯錯誤

**解決**：檢查 mock server 的錯誤日誌

### 測試連接

#### 方法 1：使用測試腳本

```bash
# Terminal 1: 啟動 mock server
python tests/mock_studio_api_server.py --port 8081 --interactive

# Terminal 2: 測試連接
python tests/test_connection.py
```

#### 方法 2：手動測試

```bash
# Terminal 1: 啟動 mock server
python tests/mock_studio_api_server.py --port 8081 --interactive

# Terminal 2: 啟動 main_speed.py
python main_speed.py

# Terminal 1: 在互動模式中
> list  # 應該看到連接的客戶端
```

### 調試步驟

1. **啟動 Mock Server 並查看日誌**
   ```bash
   python tests/mock_studio_api_server.py --port 8081 --interactive
   ```
   觀察是否有連接嘗試的日誌

2. **啟動 main_speed.py 並查看日誌**
   ```bash
   python main_speed.py
   ```
   觀察是否有連接成功的訊息

3. **使用診斷工具**
   ```bash
   python tests/diagnose_connection.py
   ```

4. **檢查網絡連接**
   ```bash
   # 測試端口是否可達
   telnet localhost 8081
   # 或
   nc -zv localhost 8081
   ```

### 如果仍然無法連接

1. **檢查防火牆**：確認沒有防火牆阻止本地連接
2. **檢查 Python 環境**：確認使用的是正確的 Python 環境和依賴
3. **查看完整錯誤日誌**：檢查 `main_speed.py` 和 mock server 的完整錯誤輸出
4. **嘗試不同的端口**：使用 `--port 8082` 等不同的端口

### 驗證連接成功的標誌

當連接成功時，你應該看到：

**Mock Server 日誌**：
```
🔌 New connection attempt from 127.0.0.1:xxxxx
📋 Connection path: /v1/ws?token=0000&id=ARO-001&device=ARO-001-1
🔗 New connection: ARO-001-ARO-001-1
✅ Sent welcome message to ARO-001-ARO-001-1
```

**main_speed.py 日誌**：
```
[timestamp] Connected to StudioAPI WebSocket
StudioAPI >>> Connected to StudioAPI WebSocket
```

**Mock Server 互動模式**：
```
> list
📋 Connected clients (1):
  - ARO-001-ARO-001-1: table_id=ARO-001, device=ARO-001-1
```

