# Mock StudioAPI Server 設置指南

## 問題診斷

如果 mock server 沒有收到客戶端連接，請檢查以下問題：

### 1. 配置文件問題

**問題**：`conf/ws.json` 可能還指向真實的 StudioAPI server，而不是 mock server。

**解決方法**：

#### 方法 A：臨時修改配置（推薦用於測試）

```bash
# 備份原始配置
cp conf/ws.json conf/ws.json.backup

# 修改為 mock server
sed -i 's|wss://studio-api.iki-cit.cc/v1/ws|ws://localhost:8081/v1/ws|g' conf/ws.json
sed -i 's|"wss://|"ws://|g' conf/ws.json

# 測試完成後恢復
# cp conf/ws.json.backup conf/ws.json
```

#### 方法 B：使用測試配置

```bash
# 使用測試配置
cp conf/ws.json.mock conf/ws.json
```

#### 方法 C：手動編輯

編輯 `conf/ws.json`，將：
```json
{
    "server_url": "wss://studio-api.iki-cit.cc/v1/ws",
    ...
}
```

改為：
```json
{
    "server_url": "ws://localhost:8081/v1/ws",
    ...
}
```

**注意**：`wss://` 改為 `ws://`（不使用 SSL）

### 2. 啟動順序

正確的啟動順序：

1. **先啟動 Mock Server**
   ```bash
   python tests/mock_studio_api_server.py --port 8081 --interactive
   ```

2. **再啟動 main_speed.py**
   ```bash
   python main_speed.py
   ```

3. **在 Mock Server 互動模式中發送訊號**
   ```
   > list
   > send ARO-001 ARO-001-1
   ```

### 3. 驗證連接

使用診斷工具檢查：

```bash
python tests/diagnose_connection.py
```

使用連接測試工具：

```bash
# Terminal 1: 啟動 mock server
python tests/mock_studio_api_server.py --port 8081

# Terminal 2: 測試連接
python tests/test_connection.py
```

### 4. 檢查 main_speed.py 日誌

啟動 `main_speed.py` 後，檢查日誌中是否有：

```
[timestamp] Connected to StudioAPI WebSocket
StudioAPI >>> Connected to StudioAPI WebSocket
```

如果沒有，可能是：
- 配置文件沒有更新
- Mock server 沒有運行
- 端口不匹配

## 快速測試流程

```bash
# 1. 更新配置（臨時）
cp conf/ws.json conf/ws.json.backup
cp conf/ws.json.mock conf/ws.json

# 2. 啟動 mock server（Terminal 1）
python tests/mock_studio_api_server.py --port 8081 --interactive

# 3. 啟動 main_speed.py（Terminal 2）
python main_speed.py

# 4. 在 mock server 互動模式中（Terminal 1）
> list          # 查看連接的客戶端
> send ARO-001 ARO-001-1  # 發送 SDP down 訊號

# 5. 檢查 main_speed.py 日誌（Terminal 2）
# 應該看到模式切換到 idle
```

## 恢復原始配置

測試完成後，恢復原始配置：

```bash
cp conf/ws.json.backup conf/ws.json
```

## 常見問題

### Q: Mock server 顯示 "No clients found"
**A**: 檢查 `conf/ws.json` 是否指向 mock server，以及 `main_speed.py` 是否已啟動並連接。

### Q: main_speed.py 無法連接到 mock server
**A**: 
- 確認 mock server 正在運行：`python tests/diagnose_connection.py`
- 確認端口匹配（默認 8081）
- 確認使用 `ws://` 而不是 `wss://`

### Q: 連接成功但沒有收到訊號
**A**: 
- 確認在 mock server 中正確發送了訊號
- 檢查 `main_speed.py` 的日誌是否有錯誤
- 確認訊號格式正確：`{"sdp": "down"}`

