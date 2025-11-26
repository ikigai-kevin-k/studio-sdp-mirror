# SDP Roulette System - Log Separation Setup

## 概述

這個系統將 SDP Roulette 的 log 輸出分離到不同的 tmux windows 中，讓開發者可以更清楚地監控不同類型的訊息。

## 檔案結構

```
studio-sdp-roulette/
├── setup_tmux_logs.sh          # 設置 tmux 會話的腳本
├── start_sdp_with_logs.sh      # 啟動系統的腳本
├── log_redirector.py           # Log 重定向模組
├── test_log_separation.py      # 測試 log 分離功能
└── README_LOG_SEPARATION.md    # 本說明文件
```

## 使用方法

### 1. 設置 tmux 會話

```bash
# 運行設置腳本（需要在現有的 dp session 中）
./setup_tmux_logs.sh
```

這會在現有的 `dp` tmux 會話中添加以下 windows：

- **bash** (window 0): Terminal window（現有）
- **sdp** (window 1): 運行 main_speed.py（現有）
- **idp** (window 2): IDP 相關 window（現有）
- **log_mqtt** (window 3): MQTT 相關 logs（新增）
- **log_api** (window 4): Table API 相關 logs（新增）
- **log_serial** (window 5): Serial port 相關 logs（新增）

### 2. 啟動系統

```bash
# 使用啟動腳本
./start_sdp_with_logs.sh
```

或者手動啟動：

```bash
# 連接到 tmux 會話
tmux attach -t dp

# 在 sdp window 中運行
python3 main_speed.py
```

### 3. 監控 logs

在 tmux 會話中，使用以下快捷鍵切換 windows：

- `Ctrl+b 0`: 切換到 bash window
- `Ctrl+b 1`: 切換到 sdp window（運行 main_speed.py）
- `Ctrl+b 2`: 切換到 idp window
- `Ctrl+b 3`: 切換到 log_mqtt window
- `Ctrl+b 4`: 切換到 log_api window
- `Ctrl+b 5`: 切換到 log_serial window

## Log 分類

### MQTT Logs (log_mqtt)
- MQTT 連線狀態
- MQTT 訊息收發
- IDP 電腦視覺辨識結果
- MQTT 錯誤訊息

### API Logs (log_api)
- Table API 呼叫 (start_post, deal_post, finish_post)
- API 回應結果
- API 錯誤訊息
- Slack 通知

### Serial Logs (log_serial)
- Serial port 連線狀態
- Serial 命令發送
- Serial 回應接收
- Serial 錯誤訊息

## Log 檔案位置

Log 檔案儲存在專案目錄的 `logs/` 資料夾下：

- `logs/sdp_mqtt.log`: MQTT logs
- `logs/sdp_api.log`: API logs
- `logs/sdp_serial.log`: Serial logs

## 測試功能

```bash
# 測試 log 分離功能
python test_log_separation.py
```

## 技術細節

### Log 重定向邏輯

`log_redirector.py` 模組提供以下函數：

- `log_mqtt(message, direction)`: 記錄 MQTT 相關訊息
- `log_api(message, direction)`: 記錄 API 相關訊息
- `log_serial(message, direction)`: 記錄 Serial 相關訊息
- `log_console(message, direction)`: 記錄到 console（重要訊息）

### 自動分類

`main_speed.py` 中的 `log_to_file()` 函數會根據訊息內容自動分類：

- 包含 "MQTT" 或 "mqtt" → MQTT logs
- 包含 "API"、"api" 或 "post" → API logs
- 包含 "Serial"、"serial"、"Receive" 或 "Send" → Serial logs
- 其他 → Console logs

## 故障排除

### 1. tmux 會話不存在

```bash
# 重新創建會話
./setup_tmux_logs.sh
```

### 2. Log 檔案權限問題

```bash
# 檢查 log 檔案權限
ls -la logs/sdp_*.log

# 如果需要，重新創建檔案
rm logs/sdp_*.log
mkdir -p logs
touch logs/sdp_mqtt.log logs/sdp_api.log logs/sdp_serial.log
```

### 3. 無法連接到 tmux 會話

```bash
# 列出所有 tmux 會話
tmux list-sessions

# 連接到特定會話
tmux attach -t sdp_logs
```

## 自定義配置

### 修改 Log 檔案位置

編輯 `log_redirector.py` 中的 `log_files` 字典：

```python
self.log_files = {
    'mqtt': 'path/to/your/mqtt.log',
    'api': 'path/to/your/api.log', 
    'serial': 'path/to/your/serial.log'
}
```

### 添加新的 Log 類型

1. 在 `log_redirector.py` 中添加新的 log 類型
2. 在 `setup_tmux_logs.sh` 中添加新的 tmux window
3. 在 `main_speed.py` 的 `log_to_file()` 函數中添加分類邏輯

## 注意事項

- 確保有足夠的磁碟空間儲存 log 檔案
- Log 檔案會持續增長，建議定期清理或設置 log rotation
- 在多個終端中同時運行可能會造成 log 檔案衝突
- 建議在生產環境中設置適當的 log 管理策略
