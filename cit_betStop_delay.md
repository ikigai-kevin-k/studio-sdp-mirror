# CIT ARO-001 Bet-Stop 延遲問題修正報告

## 📋 問題概述

**問題**: CIT ARO-001 的 bet-stop 事件總是延遲約 14 秒才觸發

**影響範圍**: 所有使用 `main_speed.py` 的 Speed Roulette 桌台（ARO-001）

**嚴重程度**: 高 - 影響遊戲流程時間準確性

---

## 🔍 問題詳情

### 觀察到的現象

根據 2025-10-09 早上的日誌記錄：

```
SDP called API tables/:gameCode/start at timestamp 1759981238487 (11:40:38.487)
Live frontend countdown & bet-stop: 11:40:51.118
SDP called API tables/:gameCode/bet-stop at timestamp 1759981265076 (11:41:05.076)
```

**時間線分析**:
- Start API 調用: `11:40:38.487`
- 前端預期 bet-stop: `11:40:51.118` (約 13 秒後)
- 實際 bet-stop API 調用: `11:41:05.076` (約 26.6 秒後)
- **延遲時間**: 約 14 秒

### 問題特徵

- 延遲時間固定為約 14 秒
- 每一局都重複發生
- 延遲時間與 `betPeriod` 設定值相關
- **不是網路問題**，而是程式邏輯錯誤

---

## 💡 根本原因分析

### 問題位置

檔案: `serial_comm/serialIO.py`

### 雙重延遲機制

程式碼中存在**兩次延遲**，導致總延遲時間為 `2 × betPeriod`:

#### 1. 第一次延遲 (第 438-443 行)

```python
threading.Timer(
    bet_period,  # 延遲 bet_period 秒 (例如: 13 秒)
    lambda t=table, r=round_id, b=bet_period: _bet_stop_countdown(
        t, r, b, token, betStop_round_for_table, get_timestamp, log_to_file
    )
).start()
```

`threading.Timer` 會在 `bet_period` 秒後執行 `_bet_stop_countdown` 函數。

#### 2. 第二次延遲 (第 681-682 行) ⚠️ **問題所在**

```python
def _bet_stop_countdown(table, round_id, bet_period, token, ...):
    try:
        # Wait for the bet period duration
        time.sleep(bet_period)  # ❌ 又延遲 bet_period 秒 (再等 13 秒)
        
        # Call bet stop for the table
        result = betStop_round_for_table(table, token)
```

### 延遲計算

假設 `betPeriod = 13` 秒:

```
總延遲 = Timer 延遲 + sleep 延遲
       = 13 秒 + 13 秒
       = 26 秒

實際延遲比預期 = 26 - 13 = 13~14 秒
```

這完全符合觀察到的現象！

---

## 🔧 修正方案

### 修改內容

**檔案**: `serial_comm/serialIO.py`

**位置**: 第 681-682 行

**修改前**:
```python
def _bet_stop_countdown(table, round_id, bet_period, token, betStop_round_for_table, get_timestamp, log_to_file):
    """
    Countdown and call bet stop for a table (non-blocking)
    """
    try:
        # Wait for the bet period duration
        time.sleep(bet_period)  # ❌ 移除這行

        # Call bet stop for the table
        print(f"[{get_timestamp()}] Calling bet stop for {table['name']} (round {round_id})")
        ...
```

**修改後**:
```python
def _bet_stop_countdown(table, round_id, bet_period, token, betStop_round_for_table, get_timestamp, log_to_file):
    """
    Countdown and call bet stop for a table (non-blocking)
    """
    try:
        # Note: Timer already handles the delay, no need to sleep here
        # Previously: time.sleep(bet_period) - removed to fix double delay issue (14s late bet-stop)

        # Call bet stop for the table
        print(f"[{get_timestamp()}] Calling bet stop for {table['name']} (round {round_id})")
        ...
```

### 修改理由

1. `threading.Timer(bet_period, ...)` 已經處理了延遲等待
2. `_bet_stop_countdown` 函數內不應該再次 `sleep`
3. 移除多餘的 `time.sleep(bet_period)` 可修正雙重延遲問題

---

## 📊 預期效果

### 修正前

```
Start API 調用 (11:40:38) 
    ↓
    [等待 13 秒] ← Timer 延遲
    ↓
_bet_stop_countdown 被觸發 (11:40:51)
    ↓
    [等待 13 秒] ← time.sleep(bet_period) 延遲
    ↓
實際調用 bet-stop API (11:41:04) ← 晚了 14 秒！
```

### 修正後

```
Start API 調用 (11:40:38) 
    ↓
    [等待 13 秒] ← Timer 延遲
    ↓
_bet_stop_countdown 被觸發 (11:40:51)
    ↓
    [立即執行] ← 移除了 time.sleep
    ↓
調用 bet-stop API (11:40:51) ← 準時！
```

---

## 🧪 測試建議

### 測試步驟

1. **部署修正**: 將修正部署到 CIT 環境
2. **啟動程式**: 執行 `main_speed.py`
3. **監控日誌**: 觀察以下時間點
   - `start` API 調用時間
   - `bet-stop` API 調用時間
   - 計算時間差

### 預期結果

- `bet-stop` API 應在 `start` API 後約 13 秒（`betPeriod` 值）調用
- 不應再有 14 秒的額外延遲
- 前端倒數計時與後端 API 調用應同步

### 驗證指標

```
時間差 = bet-stop_timestamp - start_timestamp
預期: 13 秒 (±1 秒的網路延遲容忍範圍)
修正前: 26 秒
```

---

## 📝 Git 資訊

### Branch 資訊
- **分支名稱**: `kevin/citBetStop`
- **Base 分支**: `kevin/backup`

### Commit 資訊
- **Commit ID**: `42f70ce`
- **Commit Message**: 
  ```
  WIP: Fix CIT ARO-001 bet-stop delay issue (14s late)
  
  - Remove double delay in _bet_stop_countdown function
  - threading.Timer already handles the bet_period delay
  - Previous code had time.sleep(bet_period) causing 2x delay
  - Expected: bet-stop at ~13s, Actual before fix: ~26s
  - This fixes the 14 second late bet-stop event
  
  Issue: CIT ARO-001 bet-stop event arrives 14 seconds late
  Root cause: Double delay (Timer + sleep) in serialIO.py
  ```

### 修改的檔案
- `serial_comm/serialIO.py` (2 行修改)

### GitHub PR
- **建立 PR 連結**: https://github.com/Ikigaians/studio-sdp-roulette/pull/new/kevin/citBetStop

---

## 🎯 後續行動

### 短期行動
1. ✅ 創建修正分支
2. ✅ 套用程式碼修正
3. ✅ Commit 並 push 修改
4. ⏳ 在 CIT 環境進行測試
5. ⏳ 確認 bet-stop 時間正確

### 長期行動
1. 在其他環境（UAT, STG, PRD）測試修正
2. 建立 Pull Request 進行 code review
3. 合併到主分支
4. 部署到生產環境
5. 監控生產環境運作狀況

---

## 📌 重要提醒

1. **測試優先**: 在合併到主分支前，務必在 CIT 環境充分測試
2. **監控日誌**: 測試時仔細觀察時間戳記，確認延遲已修正
3. **影響範圍**: 此修正影響所有使用 Speed Roulette 的桌台
4. **回滾計畫**: 如果出現問題，可以快速回滾到 `kevin/backup` 分支

---

## 👤 負責人

- **發現問題**: Kevin
- **分析問題**: Kevin & AI Assistant
- **修正實施**: Kevin
- **日期**: 2025-10-09

---

## 📚 相關文件

- `main_speed.py`: 主要控制程式
- `serial_comm/serialIO.py`: 序列通訊處理模組
- `table_api/sr/api_v2_sr.py`: Speed Roulette API 模組
- `conf/sr-1.json`: Speed Roulette 配置檔案

---

*文件最後更新: 2025-10-09*


