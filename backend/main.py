import os
import torch
import cv2
import numpy as np
import base64
import insightface
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLInpaintPipeline, 
    StableVideoDiffusionPipeline,
    EulerAncestralDiscreteScheduler
)
from PIL import Image
from io import BytesIO
from insightface.app import FaceAnalysis

# --- CONFIGURATION ---
IMAGE_MODEL = "AstraliteHeart/pony-diffusion-v6"
VIDEO_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="GROK007 Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL MODELS ---
# Using lazy loading for some models to save VRAM initially
pipe = None
inpaint_pipe = None
video_pipe = None
face_app = None
face_swapper = None

def load_image_models():
    global pipe, inpaint_pipe
    if pipe is None:
        print(f"Loading Image Model: {IMAGE_MODEL}...")
        pipe = StableDiffusionXLPipeline.from_pretrained(
            IMAGE_MODEL, 
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            variant="fp16" if DEVICE == "cuda" else None
        ).to(DEVICE)
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
        
    if inpaint_pipe is None:
        print("Loading Inpaint Model...")
        inpaint_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            variant="fp16" if DEVICE == "cuda" else None
        ).to(DEVICE)

def load_video_models():
    global video_pipe
    if video_pipe is None:
        print(f"Loading Video Model: {VIDEO_MODEL}...")
        video_pipe = StableVideoDiffusionPipeline.from_pretrained(
            VIDEO_MODEL, 
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            variant="fp16" if DEVICE == "cuda" else None
        ).to(DEVICE)

def load_face_models():
    global face_app, face_swapper
    if face_app is None:
        print("Loading Face Analysis Model...")
        face_app = FaceAnalysis(name='buffalo_l')
        face_app.prepare(ctx_id=0 if DEVICE == "cuda" else -1, det_size=(640, 640))
        
    if face_swapper is None:
        print("Loading Face Swapper Model...")
        # Note: inswapper_128.onnx must be in the current directory or a known path
        model_path = 'inswapper_128.onnx'
        if not os.path.exists(model_path):
            print("Downloading Face Swapper model...")
            os.system(f"wget https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx")
        face_swapper = insightface.model_zoo.get_model(model_path, download=False, preview=False)

# --- HELPERS ---
def pil_to_base64(img, format="PNG"):
    buffered = BytesIO()
    img.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def base64_to_pil(base64_str):
    if "base64," in base64_str:
        base64_str = base64_str.split("base64,")[1]
    return Image.open(BytesIO(base64.b64decode(base64_str)))

def apply_faceswap(target_img_pil, source_img_pil):
    load_face_models()
    
    target_img = cv2.cvtColor(np.array(target_img_pil), cv2.COLOR_RGB2BGR)
    source_img = cv2.cvtColor(np.array(source_img_pil), cv2.COLOR_RGB2BGR)
    
    source_faces = face_app.get(source_img)
    if not source_faces:
        return target_img_pil # No face in source
    
    source_face = source_faces[0]
    target_faces = face_app.get(target_img)
    
    res = target_img.copy()
    for face in target_faces:
        res = face_swapper.get(res, face, source_face, paste_back=True)
        
    return Image.fromarray(cv2.cvtColor(res, cv2.COLOR_BGR2RGB))

# --- ENDPOINTS ---

@app.post("/api/generate")
async def generate(
    prompt: str = Form(...),
    negative_prompt: str = Form("score_9, score_8_up, score_7_up, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"),
    face_img: str = Form(None), # Optional Base64
    width: int = Form(832),
    height: int = Form(1216),
    steps: int = Form(25)
):
    load_image_models()
    try:
        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            width=width,
            height=height
        ).images[0]
        
        if face_img:
            source_pil = base64_to_pil(face_img)
            image = apply_faceswap(image, source_pil)
            
        return {"status": "success", "image": pil_to_base64(image)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inpaint")
async def inpaint(
    image: str = Form(...), 
    mask: str = Form(...), 
    prompt: str = Form(...),
    steps: int = Form(30)
):
    load_image_models()
    try:
        init_image = base64_to_pil(image).convert("RGB")
        mask_image = base64_to_pil(mask).convert("L")
        
        output = inpaint_pipe(
            prompt=prompt,
            image=init_image,
            mask_image=mask_image,
            num_inference_steps=steps
        ).images[0]
        
        return {"status": "success", "image": pil_to_base64(output)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/animate")
async def animate(image: str = Form(...)):
    load_video_models()
    try:
        init_image = base64_to_pil(image).convert("RGB").resize((1024, 576))
        
        frames = video_pipe(
            init_image, 
            decode_chunk_size=8, 
            num_frames=25, 
            motion_bucket_id=127
        ).frames[0]
        
        # Save to MP4 and return as base64
        # (This is a simplified version, usually you'd stream or save to cloud)
        # For prototype, we'll return the first frame or a placeholder URL
        return {"status": "success", "message": "Video generated (Processing into MP4...)", "preview": pil_to_base64(frames[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
