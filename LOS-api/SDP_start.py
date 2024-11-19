import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json

url = 'https://crystal-rgs.iki-cit.cc/v1/service/sdp/table/SDP-001/start'
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZHBUb2tlbiI6IkU1TE40RU5EOVEiLCJnYW1lQ29kZSI6IlNEUC0wMDEiLCJpYXQiOjE3MzIwMDEwMzJ9.jY_f50K1To9wsaFRcd1NM6PT7VXNbjJJcHslfnUdq0M'

headers = {
    'accept': 'application/json',
    'Bearer': f'Bearer {token}',
    'x-signature': 'live-rgs-local-signature',
    'Content-Type': 'application/json'
}

data = {}
response = requests.post(url, headers=headers, json=data)
json_str = json.dumps(response.json(), indent=2)

# 添加語法高亮
colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
print(colored_json)