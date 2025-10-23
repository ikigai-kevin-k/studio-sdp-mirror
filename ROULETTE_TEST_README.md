# Roulette MQTT Command Test Scripts

這些測試腳本用於測試 Roulette ARO-001 MQTT 指令，使用重構後的 MQTT 模組。

## 測試指令

```bash
mosquitto_pub -h 192.168.88.50 -p 1883 -u "PFC" -P "wago" \
  -t "ikg/idp/ARO-001/command" \
  -m '{"command":"detect","arg":{"round_id":"ARO-001-20250825-073412","input":"rtmp://192.168.88.50:1935/live/r10_sr"}}'
```

## 預期回應格式

```json
{
  "response": "result",
  "arg": {
    "round_id": "ARO-001-20250825-073412",
    "res": 19,
    "err": 0
  }
}
```

## 測試腳本

### 1. `test_roulette_aro.py` - 主要測試腳本

這是主要的測試腳本，專門用於測試 ARO-001 指令：

```bash
python test_roulette_aro.py
```

**功能：**
- 使用 ARO-001 特定配置
- 測試實際的 MQTT 指令
- 驗證回應格式
- 提取結果值 (res)
- 驗證結果範圍 (0-36)

### 2. `test_roulette_simple.py` - 簡化測試腳本

簡化版本的測試腳本：

```bash
python test_roulette_simple.py
```

**功能：**
- 基本的指令格式測試
- 回應格式驗證
- 簡單的 MQTT 指令測試

### 3. `test_roulette_mqtt_command.py` - 完整單元測試

完整的單元測試套件：

```bash
python test_roulette_mqtt_command.py
```

**功能：**
- 完整的單元測試
- 整合測試
- 錯誤處理測試
- 格式驗證測試

## 配置檔案

### `conf/roulette-aro-broker.json`

ARO-001 特定的配置檔案：

```json
{
  "brokers": [
    {
      "broker": "192.168.88.50",
      "port": 1883,
      "username": "PFC",
      "password": "wago",
      "priority": 1
    }
  ],
  "game_config": {
    "game_type": "roulette",
    "game_code": "ARO-001",
    "command_topic": "ikg/idp/ARO-001/command",
    "response_topic": "ikg/idp/ARO-001/response",
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 1.0
  }
}
```

## 使用方法

### 基本測試

```bash
# 執行主要測試腳本
python test_roulette_aro.py
```

### 詳細測試

```bash
# 執行完整單元測試
python test_roulette_mqtt_command.py
```

### 簡化測試

```bash
# 執行簡化測試
python test_roulette_simple.py
```

## 測試結果

成功的測試會顯示：

```
🎯 Roulette Result Value: 19
🎲 Roulette Number: 19
✅ Result value is within valid range (0-36)
🎉 All tests passed! The Roulette ARO-001 MQTT command is working correctly.
```

## 錯誤處理

測試腳本會處理以下情況：

1. **連線失敗**：自動重試和錯誤報告
2. **無效回應**：格式驗證和錯誤處理
3. **超時**：30 秒超時設定
4. **無效結果**：範圍驗證 (0-36)

## 依賴項目

- `mqtt.complete_system` - 重構後的完整 MQTT 系統
- `mqtt.config_manager` - 配置管理器
- `mqtt.message_processor` - 訊息處理器
- `asyncio` - 非同步支援
- `json` - JSON 處理
- `logging` - 日誌記錄

## 注意事項

1. 確保 MQTT broker (192.168.88.50:1883) 可連線
2. 確保認證資訊正確 (PFC/wago)
3. 確保回應 topic 有正確的訊息
4. 測試結果值應在 0-36 範圍內

## 故障排除

### 連線問題
- 檢查 broker 位址和埠號
- 檢查認證資訊
- 檢查網路連線

### 回應問題
- 檢查 topic 名稱
- 檢查回應格式
- 檢查超時設定

### 結果問題
- 檢查結果值範圍
- 檢查 JSON 格式
- 檢查錯誤代碼
