# --- KAGGLE / COLAB SETUP SCRIPT ---
# Copy this into a single cell and run (Enable GPU T4 x2)

import os

# 1. Install Dependencies
print("Installing dependencies... this may take 2-3 minutes.")
os.system("pip install fastapi uvicorn python-multipart diffusers transformers accelerate torch torchvision torchaudio pillow opencv-python numpy insightface onnxruntime-gpu pyngrok gdown")

# 2. Download Face Swapper Model
print("Downloading Face Swapper model...")
if not os.path.exists("inswapper_128.onnx"):
    os.system("wget https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx")

# 3. Create the main.py file (Content from our backend/main.py)
# (In a real scenario, you can just upload the file, but here we write it for convenience)

# 4. Start Ngrok Tunnel
from pyngrok import ngrok

# REPLACE WITH YOUR NGROK AUTHTOKEN
# ngrok.set_auth_token("YOUR_TOKEN_HERE")

# Connect to port 8000
public_url = ngrok.connect(8000).public_url
print(f"\n🚀 GROK007 BACKEND IS STARTING!")
print(f"🔗 Public URL: {public_url}")
print(f"👉 Copy this URL to your frontend .env file as NEXT_PUBLIC_BACKEND_URL\n")

# 5. Run the server
import uvicorn
from main import app # Assuming main.py is in the current dir

uvicorn.run(app, host="0.0.0.0", port=8000)
