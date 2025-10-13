# 🎨 快速美化 API Response 輸出

## 🚀 **最簡單的方法**

### 1. **一行搞定 (推薦)**

```python
import json

# 美化輸出
print(json.dumps(api_response, indent=2, ensure_ascii=False))
```

### 2. **使用我們的工具**

```python
from utils.json_formatter import print_beautiful_json

# 美化輸出
print_beautiful_json(api_response, "API Response")
```

## 📝 **在你的 API 腳本中使用**

### 修改前 (醜陋輸出)
```python
# 你的原始代碼
response = api_call()
print(response)  # 醜陋的一行輸出
```

### 修改後 (美化輸出)
```python
import json

# 美化輸出
response = api_call()
print(json.dumps(response, indent=2, ensure_ascii=False))
```

## 🎯 **實際應用範例**

### 在你的 `api_v2_bcr.py` 中

```python
import json

# 獲取 API 響應
response = api_call()

# 美化輸出
print("=== BCR API Response ===")
print(json.dumps(response, indent=2, ensure_ascii=False))

# 或者只輸出特定部分
if 'data' in response and 'table' in response['data']:
    table_data = response['data']['table']
    print("\n=== Table Info ===")
    print(json.dumps(table_data, indent=2, ensure_ascii=False))
```

## 🔧 **進階選項**

### 自訂縮進和排序
```python
import json

# 4 空格縮進，不排序鍵
print(json.dumps(response, indent=4, sort_keys=False, ensure_ascii=False))

# 2 空格縮進，排序鍵
print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
```

### 使用 pprint (Python 內建)
```python
from pprint import pprint

# 簡單美化
pprint(response, indent=2, width=80)
```

## 📊 **輸出對比**

### 美化前 (醜陋)
```json
{"error":null,"data":{"table":{"gameCode":"BCR-001","gameType":"auto-sic-bo","visibility":"hidden","betPeriod":5,"name":"","pause":{"reason":"dev","createdAt":"2025-08-22T06:21:20.972Z","createdBy":"SDP"},"streams":{},"autopilot":{},"sdpConfig":{},"tableRound":{"roundId":"BCR-001-20250822-061148","gameCode":"BCR-001","gameType":"auto-sic-bo","betStopTime":"2025-08-22T06:11:53.103Z","status":"bet-txn-stopped","createdAt":"2025-08-22T06:11:48.104Z","result":{}},"metadata":{}}}}
```

### 美化後 (易讀)
```json
{
  "error": null,
  "data": {
    "table": {
      "gameCode": "BCR-001",
      "gameType": "auto-sic-bo",
      "visibility": "hidden",
      "betPeriod": 5,
      "name": "",
      "pause": {
        "reason": "dev",
        "createdAt": "2025-08-22T06:21:20.972Z",
        "createdBy": "SDP"
      },
      "streams": {},
      "autopilot": {},
      "sdpConfig": {},
      "tableRound": {
        "roundId": "BCR-001-20250822-061148",
        "gameCode": "BCR-001",
        "gameType": "auto-sic-bo",
        "betStopTime": "2025-08-22T06:11:53.103Z",
        "status": "bet-txn-stopped",
        "createdAt": "2025-08-22T06:11:48.104Z",
        "result": {}
      },
      "metadata": {}
    }
  }
}
```

## 🎉 **立即開始使用**

在你的任何 API 腳本中，只需要：

1. **導入 json 模組**
2. **替換 `print(response)` 為 `print(json.dumps(response, indent=2, ensure_ascii=False))`**

就是這麼簡單！你的 API 輸出會立即變得美觀易讀！ 🎨✨
