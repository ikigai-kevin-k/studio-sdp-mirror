# MQTT Logging Enhancement

## 概覽

本次修改解決了用戶在`log_mqtt` tmux window中看不到輪盤辨識結果的問題。現在所有相關的MQTT操作都會在MQTT日誌窗口中顯示詳細資訊。

## 修改內容

### 1. Serial IO 模組增強 (`serial_comm/serialIO.py`)

**新增的MQTT日誌輸出**：

```python
# *X;4 延遲檢測過程
log_mqtt("Waiting 10 seconds before second Roulette detect...")
log_mqtt("Starting second Roulette detect...")

# 檢測結果輸出
if result is not None and result != "" and result != []:
    log_mqtt(f"Second Roulette detect completed: {result}")
else:
    log_mqtt("Second Roulette detect completed but result is empty")

# 錯誤處理
log_mqtt(f"Error in delayed second Roulette detect: {e}")

# 等待檢測結果
log_mqtt("Waiting for IDP roulette detection result before finish post")
log_mqtt(f"Waited {elapsed_wait:.2f}s for detection result")
```

### 2. Roulette MQTT Detect 模組增強 (`roulette_mqtt_detect.py`)

**新增MQTT日誌支援**：

```python
# 導入MQTT日誌函數
try:
    from log_redirector import log_mqtt
    MQTT_LOGGING_AVAILABLE = True
except ImportError:
    MQTT_LOGGING_AVAILABLE = False
    def log_mqtt(message):
        print(f"[MQTT] {message}")

# 檢測過程日誌
log_mqtt(f"Calling Roulette detect (attempt #{_detect_count})")

# 結果日誌（帶emoji增加可讀性）
log_mqtt(f"🎯 Roulette detect successful: {result}")
log_mqtt("Roulette detect completed but result is null")
log_mqtt("Roulette detect failed")

# 錯誤日誌
log_mqtt(f"❌ Error in Roulette detect: {e}")
log_mqtt(f"❌ Error in async detect call: {e}")
```

## 新的日誌輸出範例

現在在`log_mqtt` tmux window中會看到：

```
[2025-01-27 07:04:10] MQTT >>> Detected *X;4 - Scheduling second Roulette detect after 10 seconds...
[2025-01-27 07:04:10] MQTT >>> Waiting 10 seconds before second Roulette detect...
[2025-01-27 07:04:20] MQTT >>> Starting second Roulette detect...
[2025-01-27 07:04:20] MQTT >>> Calling Roulette detect (attempt #1)
[2025-01-27 07:04:22] MQTT >>> 🎯 Roulette detect successful: 21
[2025-01-27 07:04:22] MQTT >>> Second Roulette detect completed: 21
[2025-01-27 07:04:27] MQTT >>> Waiting for IDP roulette detection result before finish post
[2025-01-27 07:04:32] MQTT >>> Waited 5.00s for detection result
```

## 關鍵改進

### 1. 完整的MQTT日誌追蹤
- 從*X;4事件到最終結果的完整追蹤
- 每個步驟都有對應的MQTT日誌輸出
- 結果值清楚顯示在MQTT窗口中

### 2. 視覺化增強
- 成功結果用🎯標示
- 錯誤訊息用❌標示
- 提高日誌的可讀性

### 3. 容錯機制
- 如果log_mqtt函數不可用，使用fallback機制
- 確保系統在任何情況下都能正常運行

### 4. 雙重日誌記錄
- 同時使用`log_mqtt`和`log_to_file`
- 確保日誌在多個地方都有記錄

## 問題解決

**修改前的問題**：
- 用戶只能在console看到結果，MQTT窗口沒有顯示
- 難以追蹤MQTT檢測的完整過程
- 結果值不在預期的日誌窗口中

**修改後的效果**：
- ✅ 所有MQTT操作都在log_mqtt窗口顯示
- ✅ 檢測結果清楚顯示，包含具體數值
- ✅ 完整的時序追蹤，從觸發到結果
- ✅ 錯誤和異常情況也有適當的日誌

## 使用說明

1. **觀察MQTT日誌**：在`log_mqtt` tmux window中可以看到完整的檢測流程
2. **結果確認**：辨識結果會用🎯標示，清楚顯示數值
3. **錯誤追蹤**：任何錯誤都會用❌標示，便於調試
4. **時序監控**：可以清楚看到每個步驟的執行時間

## Hot Reload支援

所有修改的檔案都已包含在Hot Reload監視列表中：
- `serial_comm.serialIO`
- `roulette_mqtt_detect`

使用`./reload`命令即可套用修改。

## 驗證方法

1. 啟動系統並觀察`log_mqtt` tmux window
2. 等待*X;4事件發生
3. 確認能看到完整的檢測流程日誌
4. 驗證辨識結果是否正確顯示

現在用戶應該能在`log_mqtt` tmux window中清楚地看到輪盤辨識的完整過程和結果！
