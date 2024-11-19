import requests
import json

url = 'https://crystal-rgs.iki-cit.cc/v1/service/sdp/table/SDP-001/login'
headers = {
    'accept': 'application/json',
    'x-sdp-token': 'E5LN4END9Q',
    'x-signature': 'live-rgs-local-signature',
    'Content-Type': 'application/json'  # 添加這行
}

# 空的請求體，但要確保是 JSON 格式
data = {}

# 發送 POST 請求
response = requests.post(url, headers=headers, json=data)

# 格式化輸出
print(json.dumps(response.json(), indent=2))