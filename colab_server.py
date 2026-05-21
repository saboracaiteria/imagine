# colab_server.py
#
# COMO EXECUTAR NO GOOGLE COLAB:
# 1. Crie um novo notebook no Google Colab (https://colab.research.google.com)
# 2. Defina o ambiente para GPU (Ambiente de Execução > Alterar tipo de ambiente > GPU T4)
# 3. Em uma célula, execute para instalar as dependências:
#    !pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
#    !pip install fastapi uvicorn pyngrok nest_asyncio diffusers transformers accelerate insightface onnxruntime-gpu opencv-python pillow
# 4. Copie todo o conteúdo deste arquivo para uma célula e execute.
# 5. Coloque o seu token do Ngrok (https://dashboard.ngrok.com) na variável NGROK_TOKEN abaixo.

import sys
import subprocess

# --- AUTO-INSTALAR DEPENDÊNCIAS SE ESTIVER NO COLAB ---
try:
    import torch
    if not torch.cuda.is_available():
        raise ImportError("Torch CPU detected, need GPU version")
    import pyngrok
    import nest_asyncio
    import fastapi
    import uvicorn
    import diffusers
except ImportError:
    print("⏳ Instalando dependências necessárias no Colab (isso pode levar 2-3 minutos)...")
    # Forçar a reinstalação do PyTorch com suporte a GPU (CUDA)
    subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu121"], check=True)
    # Instalar os demais pacotes
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pyngrok", "nest_asyncio", "diffusers", "transformers", "accelerate", "insightface", "onnxruntime-gpu", "opencv-python", "pillow"], check=True)
    print("✅ Instalação concluída com sucesso!")
    print("\n" + "!"*60)
    print("⚠️ ATENÇÃO: O PyTorch foi reinstalado com suporte a GPU (CUDA)!")
    print("Para aplicar as mudanças, você DEVE reiniciar a sessão do Colab:")
    print("1. Vá em 'Ambiente de execução' -> 'Reiniciar sessão' (ou 'Restart session') no menu do topo.")
    print("2. Aguarde reiniciar e clique em Play nesta célula novamente.")
    print("!"*60 + "\n")
    sys.exit(0)

import os
import time
import uuid
import torch
import gc
import cv2
import numpy as np
import base64
import tempfile
import threading
from io import BytesIO
from PIL import Image
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import nest_asyncio
import uvicorn
from pyngrok import ngrok


# --- CONFIGURAÇÃO ---
NGROK_TOKEN = "3E2BQ3BxQNIWzK36YPzpHNTrMld_5KQFpdJEGjDPtytq38SwR"  # Pegue de graça em https://dashboard.ngrok.com
PORT = 8000

app = FastAPI(title="GROK007 Colab Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Criar pasta de saídas
OUTPUTS_DIR = "./outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# --- CACHE DE MODELOS ---
pipe = None
inpaint_pipe = None
video_pipe = None
face_app = None
face_swapper = None

# Configuração do Wan 2.1-I2V
device = "cuda"

def clear_vram():
    global pipe, inpaint_pipe, video_pipe
    # Remove pipes da VRAM se necessário para evitar OOM na T4
    torch.cuda.empty_cache()
    gc.collect()

def get_image_pipe():
    global pipe
    if pipe is None:
        from diffusers import DiffusionPipeline
        clear_vram()
        print("📥 Carregando Juggernaut XL...")
        pipe = DiffusionPipeline.from_pretrained(
            "stablediffusionapi/juggernaut-xl-v9", 
            torch_dtype=torch.float16, 
            use_safetensors=True
        ).to(device)
    return pipe

def get_inpaint_pipe():
    global inpaint_pipe
    if inpaint_pipe is None:
        from diffusers import StableDiffusionXLInpaintPipeline
        clear_vram()
        print("📥 Carregando SDXL Inpaint...")
        inpaint_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
            torch_dtype=torch.float16,
            use_safetensors=True
        ).to(device)
    return inpaint_pipe

def get_video_pipe():
    global video_pipe
    if video_pipe is None:
        from diffusers import WanPipeline
        clear_vram()
        print("📥 Carregando Wan 2.1 Video...")
        # Usa WanPipeline em fp16 para caber na GPU T4 do Colab
        video_pipe = WanPipeline.from_pretrained(
            "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers", 
            torch_dtype=torch.float16
        ).to(device)
    return video_pipe

def get_face_models():
    global face_app, face_swapper
    if face_app is None:
        from insightface.app import FaceAnalysis
        face_app = FaceAnalysis(name="buffalo_l", providers=['CUDAExecutionProvider'])
        face_app.prepare(ctx_id=0, det_size=(640, 640))
    if face_swapper is None:
        import insightface
        inswapper_path = "inswapper_128.onnx"
        if not os.path.exists(inswapper_path):
            print("📥 Baixando modelo FaceSwap...")
            subprocess.run(["wget", "-O", inswapper_path, "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"], check=True)
        face_swapper = insightface.model_zoo.get_model(inswapper_path, download=False)
    return face_app, face_swapper

# --- HELPERS ---
def save_output(data_bytes: bytes, ext: str) -> str:
    filename = f"out_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(OUTPUTS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data_bytes)
    return f"outputs/{filename}"

def b64_to_pil(s):
    if "base64," in s:
        s = s.split("base64,")[1]
    return Image.open(BytesIO(base64.b64decode(s)))

# --- FILA DE JOBS DE VÍDEO ---
jobs = {}

def process_video_job(job_id, image_b64, prompt, face_img_b64):
    try:
        jobs[job_id]["logs"].append("⏳ Preparando imagens e limpando VRAM...")
        init_img = b64_to_pil(image_b64).convert("RGB")
        
        # FaceSwap opcional na imagem inicial
        if face_img_b64:
            jobs[job_id]["logs"].append("👤 Aplicando FaceSwap na imagem base...")
            app, swapper = get_face_models()
            target_cv = cv2.cvtColor(np.array(init_img), cv2.COLOR_RGB2BGR)
            source_cv = cv2.cvtColor(np.array(b64_to_pil(face_img_b64)), cv2.COLOR_RGB2BGR)
            source_faces = app.get(source_cv)
            target_faces = app.get(target_cv)
            if source_faces and target_faces:
                source_face = source_faces[0]
                for face in target_faces:
                    target_cv = swapper.get(target_cv, face, source_face, paste_back=True)
                init_img = Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))
            else:
                jobs[job_id]["logs"].append("⚠️ Rosto não detectado para FaceSwap.")

        jobs[job_id]["logs"].append("📥 Carregando Wan 2.1 I2V Model...")
        pipe = get_video_pipe()
        
        jobs[job_id]["logs"].append("🎬 Gerando frames do vídeo (Wan 2.1)...")
        # Rodando a inferência de vídeo
        video_generate = pipe(
            image=init_img,
            prompt=prompt,
            num_frames=49,
            num_inference_steps=25,
            guidance_scale=6.0,
            output_type="pil"
        ).frames[0]
        
        jobs[job_id]["logs"].append("✅ Frames gerados. Compilando com FFmpeg...")
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, frame in enumerate(video_generate):
                frame_720 = frame.resize((1280, 720), Image.LANCZOS)
                frame_720.save(os.path.join(tmpdir, f"frame_{i:04d}.png"))
                
            out_path = os.path.join(tmpdir, "output.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-framerate", "24",
                "-i", os.path.join(tmpdir, "frame_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "20", "-preset", "slow", out_path
            ], check=True, capture_output=True)
            
            with open(out_path, "rb") as f:
                video_bytes = f.read()
                
        rel_path = save_output(video_bytes, "mp4")
        jobs[job_id]["video"] = rel_path
        jobs[job_id]["status"] = "success"
        jobs[job_id]["logs"].append("🎉 Vídeo gerado com sucesso!")
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = str(e)
        jobs[job_id]["logs"].append(f"❌ Erro: {str(e)}")

# --- ROTAS ---
@app.get("/")
async def health():
    return {"status": "GROK007 Engine Online (Colab) 🚀"}

@app.get("/outputs/{filename}")
async def get_output(filename: str):
    file_path = os.path.join(OUTPUTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(file_path, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*"
    })

@app.post("/api/generate")
async def generate(prompt: str = Form(...), face_img: str = Form(None)):
    print(f"🎨 Gerando imagem: {prompt[:30]}...")
    try:
        pipe = get_image_pipe()
        image = pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=7.0,
            width=1024,
            height=1024
        ).images[0]
        
        if face_img:
            app, swapper = get_face_models()
            target_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            source_cv = cv2.cvtColor(np.array(b64_to_pil(face_img)), cv2.COLOR_RGB2BGR)
            source_faces = app.get(source_cv)
            target_faces = app.get(target_cv)
            if source_faces and target_faces:
                source_face = source_faces[0]
                for face in target_faces:
                    target_cv = swapper.get(target_cv, face, source_face, paste_back=True)
                image = Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))
                
        buf = BytesIO()
        image.save(buf, format="WEBP", quality=85)
        path = save_output(buf.getvalue(), "webp")
        return {"status": "success", "image": path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/inpaint")
async def inpaint(image: str = Form(...), mask: str = Form(...), prompt: str = Form(...)):
    print("🖌️ Processando Inpainting...")
    try:
        pipe = get_inpaint_pipe()
        output = pipe(
            prompt=prompt,
            image=b64_to_pil(image).convert("RGB"),
            mask_image=b64_to_pil(mask).convert("L"),
            num_inference_steps=25
        ).images[0]
        
        buf = BytesIO()
        output.save(buf, format="WEBP", quality=85)
        path = save_output(buf.getvalue(), "webp")
        return {"status": "success", "image": path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/animate/start")
async def animate_start(data: dict):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "logs": ["🚀 Fila iniciada..."],
        "video": None,
        "message": None
    }
    
    t = threading.Thread(
        target=process_video_job, 
        args=(job_id, data.get("image"), data.get("prompt"), data.get("face_img"))
    )
    t.start()
    return {"job_id": job_id}

@app.get("/api/animate/status")
async def animate_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job

# --- INICIAR SERVIDOR & TUNNEL ---
if __name__ == "__main__":
    if NGROK_TOKEN == "SEU_TOKEN_NGROK_AQUI" or not NGROK_TOKEN:
        print("⚠️ AVISO: Por favor, preencha a variável NGROK_TOKEN no código para expor o servidor publicamente!")
    else:
        # Configurar token do Ngrok
        ngrok.set_auth_token(NGROK_TOKEN)
        # Iniciar tunnel
        public_url = ngrok.connect(PORT, domain="joylessly-sculpture-wool.ngrok-free.dev")
        print("\n" + "="*60)
        print(f"🎉 SUAS REQUISIÇÕES ESTÃO TÚNEIS PARA O COLAB!")
        print(f"👉 URL DO COLAB PARA O PAINEL: {public_url.public_url}")
        print("="*60 + "\n")
        
    # Rodar o uvicorn em uma thread separada para evitar conflito de event loop no notebook
    print("⏳ Iniciando servidor Uvicorn em segundo plano...")
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
    )
    server_thread.daemon = True
    server_thread.start()
    
    print("🚀 Servidor online e pronto para receber requisições!")
    print("💡 Nota: A célula do Colab terminará a execução, mas o servidor continuará ativo no fundo.")
    print("Você verá os logs de requisições surgirem aqui em tempo real à medida que usar o painel.")
