import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import random
url = 'https://crystal-rgs.iki-cit.cc/v1/service/sdp/table/SDP-001/deal'
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZHBUb2tlbiI6IkU1TE40RU5EOVEiLCJnYW1lQ29kZSI6IlNEUC0wMDEiLCJpYXQiOjE3MzIwMDEwMzJ9.jY_f50K1To9wsaFRcd1NM6PT7VXNbjJJcHslfnUdq0M'

headers = {
    'accept': 'application/json',
    'Bearer': token,
    'x-signature': 'live-rgs-local-signature',
    'Content-Type': 'application/json'
}

data = {
    "roundId": "SDP-001-20241119-080725", # replaced with the roundId receive from start request
    "roulette": random.randint(0, 36) # for test, to be replaced with the actual values read from log file
}

response = requests.post(url, headers=headers, json=data)
json_str = json.dumps(response.json(), indent=2)

# 添加語法高亮
colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
print(colored_json)