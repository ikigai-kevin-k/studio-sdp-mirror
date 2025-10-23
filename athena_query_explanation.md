# Athena SQL 查詢說明

## 查詢概述
這個 SQL 查詢是用來從 AWS Athena 的日誌查詢表中提取特定時間範圍內的資料，主要用於監控和除錯特定應用程式的執行狀況。

## 完整查詢語句
```sql
SELECT 
  t1.env AS env,
  t2.app AS app,
  t3.msg AS msg,
  t4.recordTime  AS recordTime
FROM 
  ikg_prd_athena_log_query,
  UNNEST(env) WITH ORDINALITY AS t1 (env, idx1),
  UNNEST(app) WITH ORDINALITY AS t2 (app, idx2),
  UNNEST(msg) WITH ORDINALITY AS t3 (msg, idx3),
  UNNEST(recordTime) WITH ORDINALITY AS t4 (recordTime, idx4)
WHERE idx1 = idx2 and idx2 = idx3 and idx3 = idx4 and t2.app='live-table'
and dt >= date_format(from_unixtime(1756161840000/1000) at TIME ZONE 'Asia/Taipei', '%Y/%m/%d/%H/%i')
and dt <= date_format(from_unixtime(1756161959000/1000) at TIME ZONE 'Asia/Taipei', '%Y/%m/%d/%H/%i')
order by recordtime desc
limit 1000
```

## 查詢結構分析

### 1. 主要表格
- **`ikg_prd_athena_log_query`** - 包含 Athena 查詢日誌的表格

### 2. 欄位展開 (UNNEST)
查詢使用了多個 `UNNEST` 操作來展開陣列欄位：

| 欄位 | 說明 | 別名 |
|------|------|------|
| `env` | 環境變數陣列 | `t1` |
| `app` | 應用程式名稱陣列 | `t2` |
| `msg` | 訊息內容陣列 | `t3` |
| `recordTime` | 記錄時間陣列 | `t4` |

### 3. 關聯條件
```sql
WHERE idx1 = idx2 and idx2 = idx3 and idx3 = idx4
```
這確保了所有展開的陣列索引都相同，也就是說每個位置上的 `env`、`app`、`msg` 和 `recordTime` 都是對應的。

### 4. 篩選條件

#### 應用程式篩選
- `t2.app='live-table'` - 只查詢應用程式名稱為 'live-table' 的記錄

#### 時間範圍篩選
- **開始時間**: `1756161840000` (Unix timestamp in milliseconds)
- **結束時間**: `1756161959000` (Unix timestamp in milliseconds)
- **時區**: 台北時區 (Asia/Taipei)
- **格式**: 轉換為 `YYYY/MM/DD/HH/MM` 格式

### 5. 排序和限制
- **排序**: 按 `recordTime` 降序排列 (最新的記錄在前)
- **限制**: 最多返回 1000 筆記錄

## 查詢目的

這個查詢主要用於：

1. **監控**: 追蹤特定應用程式 ('live-table') 的執行狀況
2. **除錯**: 分析特定時間段內的錯誤或異常情況
3. **資料展開**: 將原本儲存為陣列的欄位展開成可讀的表格格式
4. **時間分析**: 按時間順序檢視最近的日誌記錄

## 使用場景

- 系統監控和警報
- 應用程式效能分析
- 錯誤追蹤和除錯
- 日誌審計和合規性檢查

## 注意事項

- 確保所有陣列欄位的長度一致
- 時間戳記需要正確轉換為台北時區
- 大量資料查詢可能需要較長的執行時間
- 建議根據實際需求調整 `LIMIT` 值
