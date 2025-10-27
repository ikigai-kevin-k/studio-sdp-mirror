# Roulette Detection Timing Optimization

## 概覽

本文檔說明輪盤檢測時序的最新優化，以確保IDP MQTT辨識結果能在finish post之前收到。

## 修改前的問題

1. **IDP辨識結果太慢**：辨識結果在finish post之後才收到，影響時效性
2. **First detect未整合**：*u 1時的first roulette detect功能尚未完全整合

## 修改後的時序

### 1. 禁用First Detect (*u 1)

```
*u 1 命令 → 禁用first roulette detect
         → 僅記錄"First Roulette detect disabled (IDP integration not complete)"
```

**原因**：IDP其他功能尚未完全整合，暫時禁用避免不必要的調用。

### 2. 優化Second Detect (*X;4)

```
*X;4 命令 → 立即記錄："Scheduling second Roulette detect after 10 seconds"
         → 啟動10秒延遲計時器
         → 10秒後 → 調用second roulette detect
         → 1-2秒後 → 收到辨識結果
```

**關鍵改進**：
- **延遲調用**：*X;4後等待10秒再調用detect
- **預留時間**：確保在*X;5之前有足夠時間完成辨識

### 3. Finish Post前的等待機制 (*X;5)

```
*X;5 命令 → 執行deal post
         → 等待IDP辨識結果（最多5秒）
         → 執行finish post
```

**等待邏輯**：
- 在deal post和finish post之間加入最多5秒的等待
- 確保IDP辨識結果在finish post前收到

## 完整時序流程

```
時間軸:   0s    10s   12s   15s   17s
事件:     *X;4  detect start  result  *X;5  finish

*X;4 發生 ──┐
           │
           └─ 10秒延遲 ──┐
                       │
                       └─ second detect ──┐
                                         │
                                         └─ 1-2秒 ──┐
                                                    │
                                                    └─ 收到結果
                                                            │
                                           *X;5 ────────────┼─ deal post
                                                            │
                                           等待5秒 ──────────┤
                                                            │
                                           finish post ─────┘
```

## 關鍵優勢

1. **確保時效性**：辨識結果在finish post前收到
2. **穩定的時序**：固定的10秒+5秒等待時間
3. **容錯能力**：最多5秒等待，避免無限期阻塞
4. **清晰的日誌**：每個階段都有詳細的時間戳記錄

## 日誌輸出範例

```
[2025-01-27 06:00:45] Detected *X;4 - Scheduling second Roulette detect after 10 seconds...
[2025-01-27 06:00:45] Waiting 10 seconds before second Roulette detect...
[2025-01-27 06:00:55] Starting second Roulette detect...
[2025-01-27 06:00:57] Second Roulette detect completed: 21
[2025-01-27 06:01:02] Waiting for IDP roulette detection result...
[2025-01-27 06:01:07] Waited 5.00s for detection result
================Finish================
```

## 配置參數

- **延遲時間**：10秒（*X;4到detect調用）
- **等待時間**：5秒（deal post到finish post）
- **總預留時間**：15秒確保辨識完成

## 後續改進

1. **智能等待**：實現真正的結果檢查，收到結果後立即繼續
2. **動態調整**：根據實際辨識速度動態調整延遲時間
3. **結果緩存**：將辨識結果保存供後續使用

## 注意事項

- 此修改適用於Speed Roulette系統
- Hot reload功能已包含相關MQTT模組
- 測試時請注意觀察時序日誌確認效果
