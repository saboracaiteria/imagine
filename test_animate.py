import urllib.request
import json
import base64
import time

url = 'https://ribeiro-022587--grok007-engine-fastapi-app.modal.run/api/animate/start'
with open('test_image_b64.txt', 'r') as f:
    img_b64 = f.read().strip()

data = json.dumps({
    "image": img_b64,
    "prompt": "Woman walking towards the ocean, waves breaking on the sand, realistic fluid movement",
    "face_img": None
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

print("Sending request...")
start = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as response:
        print('Status Code:', response.getcode())
        resp_data = response.read().decode('utf-8')
        print('Response:', resp_data[:200])
except Exception as e:
    print('Error:', str(e))
print("Time elapsed:", time.time() - start)
