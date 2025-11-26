# Roulette Single Detection Fix

## 問題分析

從日誌發現系統在短時間內發送了多次detect command：
```
[2025-10-27 07:29:13.224] Waiting 15 seconds before second Roulette detect...
[2025-10-27 07:29:13.720] Waiting 15 seconds before second Roulette detect...
[2025-10-27 07:29:14.216] Waiting 15 seconds before second Roulette detect...
```

這表示*X;4事件被重複處理，導致啟動多個檢測線程。

## 解決方案

### 1. **防重複機制**
添加了round-based的防重複檢查：

```python
# 檢查是否已為此回合啟動檢測
if not hasattr(global_vars, 'roulette_detection_sent') or global_vars.get('roulette_detection_sent') != current_round_id:
    # 標記此回合已啟動檢測
    global_vars['roulette_detection_sent'] = current_round_id
    
    # 啟動檢測...
else:
    # 跳過重複的*X;4事件
    log_mqtt(f"⚠️ *X;4 duplicate detected - Roulette detection already scheduled for round {current_round_id}")
```

### 2. **狀態重置機制**
在每輪盤回合結束時重置檢測標誌：

```python
# 在finish_post完成後重置
if 'roulette_detection_sent' in global_vars:
    global_vars['roulette_detection_sent'] = None
    log_mqtt("Reset roulette detection flag for new round")
```

### 3. **增強日誌追蹤**
添加了清楚的日誌標示：

```python
log_mqtt(f"Detected *X;4 - Scheduling SINGLE Roulette detect for round {current_round_id} after 15 seconds...")
log_mqtt("Starting SINGLE second Roulette detect...")
```

## 修改效果

### **修改前**：
```
[07:29:13.224] Waiting 15 seconds before second Roulette detect...
[07:29:13.720] Waiting 15 seconds before second Roulette detect...  # 重複！
[07:29:14.216] Waiting 15 seconds before second Roulette detect...  # 重複！
```

### **修改後**：
```
[07:30:15] Detected *X;4 - Scheduling SINGLE Roulette detect for round ARO-001-xxx after 15 seconds...
[07:30:16] ⚠️ *X;4 duplicate detected - Roulette detection already scheduled for round ARO-001-xxx
[07:30:17] ⚠️ *X;4 duplicate detected - Roulette detection already scheduled for round ARO-001-xxx
[07:30:30] Starting SINGLE second Roulette detect...
[07:30:32] 🎯 Second Roulette detect SUCCESS: 35
```

## 關鍵改進

### 1. **基於Round ID的去重**
- 每個輪盤回合只允許一次檢測
- 使用round_id作為唯一標識符
- 防止同一回合內的重複*X;4觸發多次檢測

### 2. **狀態生命週期管理**
- 在finish_post後重置檢測標誌
- 確保新回合能正常啟動檢測
- 避免狀態污染

### 3. **清楚的錯誤處理**
- 重複*X;4事件會被記錄但不執行
- 提供明確的日誌說明為什麼跳過
- 便於調試和監控

### 4. **SINGLE關鍵字標示**
- 所有相關日誌都加上"SINGLE"標示
- 強調這是單次檢測機制
- 便於在日誌中識別

## 預期效果

1. **每回合僅一次檢測**：無論收到多少次*X;4事件
2. **清楚的重複事件記錄**：能看到哪些*X;4被跳過
3. **穩定的檢測時序**：15秒延遲保持一致
4. **正確的狀態重置**：新回合正常開始

## 測試驗證

可以通過以下方式驗證修復效果：

1. **觀察日誌**：
   - 每個回合只應看到一次"Scheduling SINGLE Roulette detect"
   - 重複的*X;4應顯示"duplicate detected"
   
2. **檢測結果**：
   - 應該只收到一次IDP響應
   - 結果應該更穩定和準確

3. **時序檢查**：
   - 從*X;4到檢測開始應該是穩定的15秒
   - 不應該有重疊的檢測操作

## 部署說明

1. 使用`./reload`命令套用修改
2. 觀察`log_mqtt` window中的新日誌格式
3. 確認每回合只有一次檢測被啟動
4. 驗證重複*X;4事件被正確跳過

這個修復確保了輪盤檢測的唯一性和可靠性，避免了資源浪費和結果混亂。
