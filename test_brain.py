import urllib.request
import urllib.parse
import json

url = 'https://ribeiro-022587--grok007-engine-fastapi-app.modal.run/api/refine'
data = urllib.parse.urlencode({'prompt': 'mulher caminhando na praia em direçao ao mar, ondas quebrando na areia'}).encode('utf-8')

print("Testing Qwen2-Brain AI refinement...")
try:
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=60) as response:
        print("Status Code:", response.getcode())
        result = json.loads(response.read().decode('utf-8'))
        print("Result JSON:", json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
