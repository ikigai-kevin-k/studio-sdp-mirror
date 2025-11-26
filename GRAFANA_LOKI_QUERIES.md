# Grafana Loki 查詢指南 - Sensor Error Logs

## 概述

本文件說明如何在 Grafana Explore 中使用 LogQL 查詢 sensor error log 資料。

## 資料結構

### Stream Labels

Sensor error 資料使用以下 labels：

```json
{
  "job": "speed_roulette_sensor_errors",  // 或 "vip_roulette_sensor_errors"
  "instance": "GC-ARO-001-1",
  "game_type": "speed",  // 或 "vip"
  "event_type": "sensor_error",
  "source": "sensor_err_table"
}
```

### Log Entry 格式 (JSON)

每個 log entry 是 JSON 格式，包含以下欄位：

```json
{
  "log_file": "speed_2025-11-11.log",
  "date": "2025-11-11",
  "time": "09:10:12.891",
  "datetime": "2025-11-11 09:10:12.891",
  "message": "*X;6;182;28;4;006;0"
}
```

## 基本查詢

### 1. 查詢所有 Speed Sensor Errors

```logql
{job="speed_roulette_sensor_errors"}
```

### 2. 查詢所有 VIP Sensor Errors

```logql
{job="vip_roulette_sensor_errors"}
```

### 3. 查詢所有 Sensor Errors (Speed + VIP)

```logql
{event_type="sensor_error"}
```

或使用正則表達式：

```logql
{job=~".*_roulette_sensor_errors"}
```

## 進階查詢

### 4. 按 Game Type 篩選

```logql
{job="speed_roulette_sensor_errors", game_type="speed"}
```

```logql
{job="vip_roulette_sensor_errors", game_type="vip"}
```

### 5. 解析 JSON 並顯示欄位

```logql
{job="speed_roulette_sensor_errors"}
| json
```

這會解析 JSON 並顯示所有欄位。

### 6. 按日期篩選

```logql
{job="speed_roulette_sensor_errors"}
| json
| date = "2025-11-11"
```

### 7. 按時間範圍篩選

```logql
{job="speed_roulette_sensor_errors"}
| json
| date >= "2025-11-10" and date <= "2025-11-11"
```

### 8. 按 Log File 篩選

```logql
{job="speed_roulette_sensor_errors"}
| json
| log_file = "speed_2025-11-11.log"
```

### 9. 按 Message 內容篩選

查詢特定錯誤碼：

```logql
{job="speed_roulette_sensor_errors"}
| json
| message =~ ".*;4;.*"
```

查詢包含特定數值的訊息：

```logql
{job="speed_roulette_sensor_errors"}
| json
| message =~ ".*182;28.*"
```

### 10. 提取並顯示特定欄位

```logql
{job="speed_roulette_sensor_errors"}
| json
| line_format "{{.datetime}} | {{.message}} | {{.log_file}}"
```

### 11. 統計查詢

計算每個日期的錯誤數量：

```logql
sum by (date) (
  count_over_time(
    {job="speed_roulette_sensor_errors"}
    | json
    [1d]
  )
)
```

計算每小時的錯誤數量：

```logql
sum by (hour) (
  count_over_time(
    {job="speed_roulette_sensor_errors"}
    | json
    [1h]
  )
)
```

## 時間範圍查詢

### 12. 最近 1 小時的錯誤

```logql
{job="speed_roulette_sensor_errors"}[1h]
```

### 13. 最近 24 小時的錯誤

```logql
{job="speed_roulette_sensor_errors"}[24h]
```

### 14. 最近 7 天的錯誤

```logql
{job="speed_roulette_sensor_errors"}[7d]
```

## 實用查詢範例

### 範例 1: 查看今天的 Sensor Errors

```logql
{job="speed_roulette_sensor_errors"}
| json
| date = "2025-11-11"
| line_format "{{.time}} | {{.message}}"
```

### 範例 2: 統計每個 Log File 的錯誤數量

```logql
sum by (log_file) (
  count_over_time(
    {job="speed_roulette_sensor_errors"}
    | json
    [1d]
  )
)
```

### 範例 3: 查找特定錯誤碼的出現次數

```logql
sum by (message) (
  count_over_time(
    {job="speed_roulette_sensor_errors"}
    | json
    | message =~ ".*;4;.*"
    [1d]
  )
)
```

### 範例 4: 按日期分組顯示錯誤

```logql
{job="speed_roulette_sensor_errors"}
| json
| line_format "{{.date}} {{.time}} | {{.message}}"
```

### 範例 5: 比較 Speed 和 VIP 的錯誤

```logql
{job=~"speed_roulette_sensor_errors|vip_roulette_sensor_errors"}
| json
| line_format "{{.game_type}} | {{.date}} {{.time}} | {{.message}}"
```

## 在 Grafana Explore 中使用

### 步驟 1: 開啟 Grafana Explore

1. 登入 Grafana
2. 點擊左側選單的 **Explore** 圖示 (指南針圖示)
3. 在右上角選擇 **Loki** 資料源

### 步驟 2: 輸入查詢

1. 在查詢輸入框中輸入 LogQL 查詢
2. 例如：`{job="speed_roulette_sensor_errors"}`

### 步驟 3: 設定時間範圍

1. 在右上角選擇時間範圍
2. 可以選擇預設範圍（如 Last 1 hour, Last 24 hours）
3. 或使用自訂時間範圍

### 步驟 4: 執行查詢

1. 點擊 **Run query** 按鈕
2. 結果會顯示在下方

### 步驟 5: 切換顯示模式

- **Logs**: 顯示原始日誌條目
- **Table**: 以表格形式顯示（適合 JSON 資料）
- **Stats**: 顯示統計資訊

## 建立 Dashboard

### 建立 Sensor Error 統計面板

1. 建立新的 Dashboard
2. 新增 Panel
3. 選擇 **Loki** 資料源
4. 使用以下查詢：

```logql
sum(count_over_time({job="speed_roulette_sensor_errors"}[1h]))
```

這會顯示每小時的錯誤總數。

### 建立時間序列圖表

```logql
sum by (date) (
  count_over_time(
    {job="speed_roulette_sensor_errors"}
    | json
    [1h]
  )
)
```

### 建立表格面板

使用 Table 視覺化，查詢：

```logql
{job="speed_roulette_sensor_errors"}
| json
| line_format "{{.date}} | {{.time}} | {{.message}}"
```

## 常用查詢快捷方式

### 快速查詢今日錯誤

```logql
{job="speed_roulette_sensor_errors"}
| json
| date = "2025-11-11"
```

### 快速查詢最近錯誤

```logql
{job="speed_roulette_sensor_errors"}[1h]
```

### 快速統計錯誤數量

```logql
count_over_time({job="speed_roulette_sensor_errors"}[1d])
```

## 除錯查詢

### 檢查資料是否存在

```logql
{job="speed_roulette_sensor_errors"}
```

如果沒有結果，檢查：
1. 資料是否已推送到 Loki
2. Labels 是否正確
3. 時間範圍是否正確

### 檢查 JSON 格式

```logql
{job="speed_roulette_sensor_errors"}
| json
```

如果解析失敗，檢查 JSON 格式是否正確。

## 參考資料

- [LogQL 官方文件](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Explore 文件](https://grafana.com/docs/grafana/latest/explore/)
- [Loki 查詢語法](https://grafana.com/docs/loki/latest/logql/log_queries/)

## 標籤說明

| Label | 說明 | 可能值 |
|-------|------|--------|
| `job` | 工作類型 | `speed_roulette_sensor_errors`, `vip_roulette_sensor_errors` |
| `instance` | 實例標識 | `GC-ARO-001-1` |
| `game_type` | 遊戲類型 | `speed`, `vip` |
| `event_type` | 事件類型 | `sensor_error` |
| `source` | 資料來源 | `sensor_err_table` |

## JSON 欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| `log_file` | 來源日誌檔案 | `speed_2025-11-11.log` |
| `date` | 日期 | `2025-11-11` |
| `time` | 時間 | `09:10:12.891` |
| `datetime` | 完整日期時間 | `2025-11-11 09:10:12.891` |
| `message` | 錯誤訊息 | `*X;6;182;28;4;006;0` |

