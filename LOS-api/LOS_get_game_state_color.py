import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json

url = 'https://crystal-rgs.iki-cit.cc/v1/service/table/SDP-001'
headers = {
    'accept': 'application/json',
    'x-signature': 'live-rgs-local-signature'
}

response = requests.get(url, headers=headers)
json_str = json.dumps(response.json(), indent=2)

# 添加語法高亮
colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
print(colored_json)