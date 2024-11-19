import requests
import json

url = 'https://crystal-rgs.iki-cit.cc/v1/service/table/SDP-001'
headers = {
    'accept': 'application/json',
    'x-signature': 'live-rgs-local-signature'
}

# 發送 GET 請求
response = requests.get(url, headers=headers)

# 格式化輸出 JSON
print(json.dumps(response.json(), indent=2))
print(json.dumps(response.json()['data'], indent=2))