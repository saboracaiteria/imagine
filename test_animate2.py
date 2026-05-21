import urllib.request
import json
import base64
import time
from PIL import Image
import io
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

url = 'https://ribeiro-022587--grok007-engine-fastapi-app.modal.run/api/animate'

# Create a 1024x576 image and encode as base64 jpeg
img = Image.new('RGB', (1024, 576), color = (73, 109, 137))
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG', quality=85)
img_b64 = "data:image/jpeg;base64," + base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

data = json.dumps({
    "image": img_b64,
    "prompt": "test motion",
    "face_img": None
}).encode('utf-8')

print("Sending request size:", len(data), "bytes")
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

start = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as response:
        print('Status Code:', response.getcode())
        resp_data = response.read().decode('utf-8')
        print('Response:', resp_data[:200])
except Exception as e:
    print('Error:', str(e))
print("Time elapsed:", time.time() - start)
