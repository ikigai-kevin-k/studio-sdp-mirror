# Loki LogQL 查詢指令指南

## 概述

本文件提供完整的 LogQL (Log Query Language) 查詢指令，用於查詢推送到 Loki 的日誌資料。

## 基本語法

### 1. 標籤選擇器 (Label Selectors)

```logql
{job="speed_roulette_logs"}
```

使用多個標籤：

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
```

使用正則表達式：

```logql
{job="speed_roulette_logs", instance=~"GC-ARO-001-.*"}
```

### 2. 時間範圍查詢

```logql
{job="speed_roulette_logs"}[1h]    # 最近 1 小時
{job="speed_roulette_logs"}[24h]   # 最近 24 小時
{job="speed_roulette_logs"}[7d]    # 最近 7 天
```

## Speed Roulette Logs 查詢

### 基本查詢

#### 查詢所有 Speed Roulette 日誌

```logql
{job="speed_roulette_logs"}
```

#### 查詢特定 Instance (ARO-001-2)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
```

#### 查詢特定 Instance (ARO-001-1)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-1"}
```

#### 查詢所有 ARO-001 的日誌 (包含 -1 和 -2)

```logql
{job="speed_roulette_logs", instance=~"GC-ARO-001-.*"}
```

#### 按遊戲類型篩選

```logql
{job="speed_roulette_logs", game_type="speed"}
```

#### 按日誌日期篩選

```logql
{job="speed_roulette_logs", log_date="2025-11-18"}
```

#### 組合查詢 (ARO-001-2 今天的日誌)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2", log_date="2025-11-18"}
```

### JSON 解析和過濾

Speed Roulette 日誌是 JSON 格式，需要解析：

#### 解析 JSON

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
```

#### 解析並顯示特定欄位

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| line_format "{{.timestamp}} | {{.type}} | {{.direction}} | {{.message}}"
```

#### 按日誌類型篩選 (只顯示 Receive)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| type = "Receive"
```

#### 按日誌類型篩選 (只顯示 Send)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| type = "Send"
```

#### 按方向篩選 (只顯示接收的日誌)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| direction = ">>>"
```

#### 按方向篩選 (只顯示發送的日誌)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| direction = "<<<"
```

#### 按訊息內容篩選 (包含特定字串)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*X;6.*"
```

#### 按訊息內容篩選 (包含錯誤碼)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*ERROR.*"
```

### 時間範圍查詢

#### 最近 1 小時的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
```

#### 最近 24 小時的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[24h]
```

#### 最近 7 天的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[7d]
```

#### 最近 1 小時的 Receive 日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
| json
| type = "Receive"
```

## 統計查詢

### 計算日誌條目數量

#### 計算總日誌條目數

```logql
count_over_time({job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h])
```

#### 按類型分組統計

```logql
sum by (type) (
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2"}
    | json
    [1h]
  )
)
```

#### 按日期分組統計

```logql
sum by (log_date) (
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2"}
    [24h]
  )
)
```

#### 每小時的日誌數量

```logql
sum by (hour) (
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2"}
    [24h]
  )
)
```

#### 按 Instance 分組統計

```logql
sum by (instance) (
  count_over_time(
    {job="speed_roulette_logs"}
    [1h]
  )
)
```

### 速率查詢 (Rate Queries)

#### 每秒日誌條目數

```logql
rate({job="speed_roulette_logs", instance="GC-ARO-001-2"}[1m])
```

#### 每分鐘日誌條目數

```logql
rate({job="speed_roulette_logs", instance="GC-ARO-001-2"}[5m]) * 60
```

## 進階查詢

### 查找特定錯誤訊息

#### 查找包含 "*X;6" 的日誌 (Sensor Error)

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*\\*X;6.*"
```

#### 查找包含 "ERROR" 的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*ERROR.*"
```

#### 查找包含特定序列號的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*151;23.*"
```

### 比較查詢

#### 比較兩個 Instance 的日誌

```logql
{job="speed_roulette_logs", instance=~"GC-ARO-001-.*"}
| json
| line_format "{{.instance}} | {{.timestamp}} | {{.message}}"
```

### 時間序列查詢

#### 每 5 分鐘的日誌數量

```logql
sum(
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2"}
    [5m]
  )
)
```

#### 每小時的日誌數量 (時間序列)

```logql
sum(
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2"}
    [1h]
  )
)
```

## 實用查詢範例

### 範例 1: 查看 ARO-001-2 最近的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
| json
| line_format "{{.timestamp}} | {{.type}} {{.direction}} {{.message}}"
```

### 範例 2: 查看今天的 Receive 日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2", log_date="2025-11-18"}
| json
| type = "Receive"
| line_format "{{.timestamp}} | {{.message}}"
```

### 範例 3: 統計今天的日誌類型分布

```logql
sum by (type) (
  count_over_time(
    {job="speed_roulette_logs", instance="GC-ARO-001-2", log_date="2025-11-18"}
    | json
    [1d]
  )
)
```

### 範例 4: 查找最近的錯誤

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
| json
| message =~ ".*(ERROR|error|Error|\\*X;6).*"
| line_format "{{.timestamp}} | {{.message}}"
```

### 範例 5: 比較 ARO-001-1 和 ARO-001-2 的日誌數量

```logql
sum by (instance) (
  count_over_time(
    {job="speed_roulette_logs", instance=~"GC-ARO-001-.*"}
    [1h]
  )
)
```

## 在 Grafana 中使用

### 步驟 1: 開啟 Grafana Explore

1. 登入 Grafana
2. 點擊左側選單的 **Explore** 圖示 (指南針圖示)
3. 在右上角選擇 **Loki** 資料源

### 步驟 2: 輸入查詢

在查詢輸入框中輸入 LogQL 查詢，例如：

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
```

### 步驟 3: 設定時間範圍

在右上角選擇時間範圍：
- Last 1 hour
- Last 24 hours
- Last 7 days
- 或自訂時間範圍

### 步驟 4: 執行查詢

點擊 **Run query** 按鈕，結果會顯示在下方。

### 步驟 5: 切換顯示模式

- **Logs**: 顯示原始日誌條目
- **Table**: 以表格形式顯示（適合 JSON 資料）
- **Stats**: 顯示統計資訊

## 使用 API 查詢

### 使用 verify_loki_logs.py 腳本

```bash
# 驗證 ARO-001-2 的日誌
python3 verify_loki_logs.py --hours 24

# 驗證特定 instance
python3 verify_loki_logs.py --instance GC-ARO-001-2 --hours 24
```

### 直接使用 curl 查詢

#### 查詢最近 1 小時的日誌

```bash
curl -G -s "http://100.64.0.113:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="speed_roulette_logs", instance="GC-ARO-001-2"}' \
  --data-urlencode 'start='$(date -d '1 hour ago' +%s)000000000 \
  --data-urlencode 'end='$(date +%s)000000000 \
  --data-urlencode 'limit=100' | jq
```

#### 即時查詢

```bash
curl -G -s "http://100.64.0.113:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="speed_roulette_logs", instance="GC-ARO-001-2"}' \
  --data-urlencode 'limit=100' | jq
```

## 標籤說明

| Label | 說明 | 可能值 |
|-------|------|--------|
| `job` | 工作類型 | `speed_roulette_logs`, `speed_roulette_error_logs` |
| `instance` | 實例標識 | `GC-ARO-001-1`, `GC-ARO-001-2`, `GC-ARO-002-1`, `GC-ARO-002-2` |
| `game_type` | 遊戲類型 | `speed`, `vip` |
| `log_type` | 日誌類型 | `application_log` |
| `source` | 資料來源 | `speed_log_file` |
| `log_date` | 日誌日期 | `2025-11-18` |

## JSON 欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| `timestamp` | ISO 格式時間戳 | `2025-11-18T12:51:30.270000` |
| `type` | 日誌類型 | `Receive`, `Send`, `API`, `MQTT` |
| `direction` | 方向 | `>>>` (接收), `<<<` (發送) |
| `message` | 日誌訊息 | `*X;2;151;23;0;161;0` |
| `raw_line` | 原始日誌行 | 完整的原始日誌行 |

## 常用快捷查詢

### 快速查看 ARO-001-2 最近的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h]
```

### 快速統計日誌數量

```logql
count_over_time({job="speed_roulette_logs", instance="GC-ARO-001-2"}[1h])
```

### 快速查看今天的日誌

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2", log_date="2025-11-18"}
```

### 快速查找錯誤

```logql
{job="speed_roulette_logs", instance="GC-ARO-001-2"}
| json
| message =~ ".*(ERROR|\\*X;6).*"
```

## 參考資料

- [LogQL 官方文件](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Explore 文件](https://grafana.com/docs/grafana/latest/explore/)
- [Loki 查詢語法](https://grafana.com/docs/loki/latest/logql/log_queries/)
- [Loki API 文件](https://grafana.com/docs/loki/latest/api/)

