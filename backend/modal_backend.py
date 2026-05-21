import os
import modal
import time

# Disco persistente para guardar modelos (não baixa de novo)
volume = modal.Volume.from_name("grok007-models", create_if_missing=True)
MODEL_DIR = "/models"

image = (
    modal.Image.debian_slim()
    .apt_install("git", "wget", "cmake", "libgl1-mesa-glx", "libglib2.0-0", "ffmpeg")
    .pip_install(
        "fastapi",
        "uvicorn",
        "python-multipart",
        "git+https://github.com/huggingface/diffusers.git",
        "transformers",
        "accelerate",
        "torch",
        "torchvision",
        "insightface",
        "onnxruntime-gpu",
        "opencv-python",
        "pillow",
        "xformers",
        "peft",
        "sentencepiece",
        "deep-translator",
        "bitsandbytes",
        "ftfy",
    )
)

app = modal.App("grok007-engine")

# Armazena logs de cada task
job_logs = modal.Dict.from_name("grok007-job-logs", create_if_missing=True)


@app.function(image=image, volumes={MODEL_DIR: volume}, timeout=3600)
def download_models():
    """Baixa e commita os modelos no volume persistente (rodar uma vez)."""
    import torch
    from diffusers import StableDiffusionXLPipeline, StableDiffusionXLInpaintPipeline
    import os
    import subprocess

    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Novo modelo: Juggernaut XL (Focado em Realismo e sem censura)
    realism_path = f"{MODEL_DIR}/juggernaut-xl"
    inpaint_path = f"{MODEL_DIR}/sdxl-inpaint"
    inswapper_path = f"{MODEL_DIR}/inswapper_128.onnx"

    from diffusers import DiffusionPipeline, StableDiffusionXLInpaintPipeline
    import shutil

    # Remove o modelo antigo (Pony) se existir
    old_pony = f"{MODEL_DIR}/pony-diffusion-v6"
    if os.path.exists(old_pony):
        print("🗑️ Removendo Pony Diffusion antigo...")
        shutil.rmtree(old_pony)
    
    if not os.path.exists(realism_path):
        print("📥 Baixando Juggernaut XL (Realismo Extremo)...")
        # Usando a versão oficial do Juggernaut XL v9 (sem variant fp16 se não existir)
        pipe = DiffusionPipeline.from_pretrained("stablediffusionapi/juggernaut-xl-v9", torch_dtype=torch.float16, use_safetensors=True)
        pipe.save_pretrained(realism_path)
    
    if not os.path.exists(f"{MODEL_DIR}/wan-2.1-i2v"):
        print("📥 Baixando Wan 2.1-I2V (O Rei dos Vídeos - 14B Params)...")
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id="Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
            local_dir=f"{MODEL_DIR}/wan-2.1-i2v",
            local_dir_use_symlinks=False
        )


    if not os.path.exists(inswapper_path):
        print("📥 Baixando FaceSwap model...")
        import subprocess
        subprocess.run(["wget", "-O", inswapper_path, "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"], check=True)

    if not os.path.exists(f"{MODEL_DIR}/qwen2"):
        print("📥 Baixando Cérebro (Qwen2-1.5B-Instruct)...")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_name = "Qwen/Qwen2-1.5B-Instruct"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16)
        tokenizer.save_pretrained(f"{MODEL_DIR}/qwen2")
        model.save_pretrained(f"{MODEL_DIR}/qwen2")

    if not os.path.exists(f"{MODEL_DIR}/vision"):
        print("📥 Baixando Olhos (BLIP Vision)...")
        from transformers import BlipProcessor, BlipForConditionalGeneration
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", torch_dtype=torch.float16)
        processor.save_pretrained(f"{MODEL_DIR}/vision")
        model.save_pretrained(f"{MODEL_DIR}/vision")

    print("💾 Commitando no volume...")
    volume.commit()
    print("✅ Sucesso! Modelos salvos permanentemente.")

def save_output_file(data_bytes: bytes, extension: str) -> str:
    """Salva os bytes em /models/outputs/ com um nome único e retorna a rota relativa."""
    import os
    import uuid
    import time
    
    outputs_dir = os.path.join(MODEL_DIR, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    filename = f"out_{int(time.time())}_{uuid.uuid4().hex[:8]}.{extension}"
    file_path = os.path.join(outputs_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(data_bytes)
    
    # Commita no volume persistente do Modal
    volume.commit()
    print(f"💾 Arquivo salvo no volume: {file_path}")
    return f"outputs/{filename}"

@app.cls(
    gpu="T4",
    memory=8192,
    volumes={MODEL_DIR: volume},
    image=image,
    scaledown_window=300,
    timeout=600,
)
class HelperEngine:
    @modal.enter()
    def load_models(self):
        self.brain_model = None
        self.brain_tokenizer = None
        self.vision_model = None
        self.vision_processor = None

    def _get_brain(self):
        if self.brain_model is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            local_path = f"{MODEL_DIR}/qwen2"
            if os.path.isdir(local_path) and os.listdir(local_path):
                path = local_path
                print(f"⚡ Cérebro (Brain AI) encontrado localmente: {path}")
            else:
                path = "Qwen/Qwen2-1.5B-Instruct"
                print(f"⚡ Baixando Cérebro (Brain AI) do HuggingFace: {path}")
            
            self.brain_tokenizer = AutoTokenizer.from_pretrained(path)
            self.brain_model = AutoModelForCausalLM.from_pretrained(
                path, torch_dtype=torch.float16, device_map="auto"
            )
        return self.brain_model, self.brain_tokenizer

    def _get_vision(self):
        if self.vision_model is None:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            local_path = f"{MODEL_DIR}/vision"
            if os.path.isdir(local_path) and os.listdir(local_path):
                path = local_path
                print(f"⚡ Visão (BLIP) encontrada localmente: {path}")
            else:
                path = "Salesforce/blip-image-captioning-base"
                print(f"⚡ Baixando Visão (BLIP) do HuggingFace: {path}")

            self.vision_processor = BlipProcessor.from_pretrained(path)
            self.vision_model = BlipForConditionalGeneration.from_pretrained(
                path, torch_dtype=torch.float16
            ).to("cuda")
        return self.vision_model, self.vision_processor

    @modal.method()
    def describe_image(self, image_b64: str) -> str:
        """Usa o BLIP para entender o que há na imagem."""
        from PIL import Image
        from io import BytesIO
        import base64
        import torch
        
        if "base64," in image_b64: image_b64 = image_b64.split("base64,")[1]
        raw_image = Image.open(BytesIO(base64.b64decode(image_b64))).convert('RGB')
        
        model, processor = self._get_vision()
        inputs = processor(raw_image, return_tensors="pt").to("cuda", torch.float16)
        out = model.generate(**inputs)
        description = processor.decode(out[0], skip_special_tokens=True)
        return description

    @modal.method()
    def refine_prompt(self, prompt: str, context: str = "") -> str:
        """Usa o Qwen2 para expandir o prompt considerando o contexto da imagem."""
        model, tokenizer = self._get_brain()
        system_msg = (
            "You are GrokEngine Brain. Your task is to combine the user's motion request with the visual context "
            "of the image to create a hyper-realistic, highly dynamic animation prompt. "
            "If the user asks for actions like 'walking', 'going to', or 'moving', describe the full physical progression: "
            "the shift in weight, the change in perspective, and the environmental interaction. "
            "Focus on physics-based movement and maintaining anatomical structure. "
            "Output ONLY the final prompt in English."
        )
        user_msg = f"Visual context: {context}\nMotion request: {prompt}\nRefine for hyper-realism:"
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([text], return_tensors="pt").to("cuda")
        
        generated_ids = model.generate(inputs.input_ids, max_new_tokens=150, do_sample=True, temperature=0.7)
        response = tokenizer.batch_decode(generated_ids[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        return response.strip()

@app.cls(
    gpu="A100-40GB",
    memory=65536,
    volumes={MODEL_DIR: volume},
    image=image,
    scaledown_window=300, 
    timeout=1200, 
)
class GrokEngine:
    @modal.enter()
    def load_models(self):
        """Prepara os caminhos."""
        self.realism_path = f"{MODEL_DIR}/juggernaut-xl"
        self.inpaint_path = f"{MODEL_DIR}/sdxl-inpaint"
        self.inswapper_path = f"{MODEL_DIR}/inswapper_128.onnx"
        self.video_path = f"{MODEL_DIR}/wan-2.1-i2v"
        
        # Atributos de modelo para carregamento preguiçoso
        self.pipe = None
        self.inpaint_pipe = None
        self.video_pipe = None
        self.face_swapper = None
        self.face_app = None

    def _translate(self, text: str) -> str:
        """Traduz texto PT→EN usando Google Translate. Vocabulário completo."""
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source='pt', target='en').translate(text)
            if result:
                return result
        except Exception as e:
            print(f"⚠️ Google Translate falhou: {e}")
        return text  # fallback: retorna o original

    def _get_pipe(self):
        if self.pipe is None:
            import torch
            from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
            if not os.path.exists(self.realism_path):
                raise Exception("Erro: Modelo Juggernaut não encontrado.")
            
            print("⚡ Carregando Juggernaut XL (Motor de Realismo)...")
            self.pipe = StableDiffusionXLPipeline.from_pretrained(
                self.realism_path, torch_dtype=torch.float16, local_files_only=True
            )
            self.pipe.enable_model_cpu_offload()
            
            # Scheduler otimizado para o Juggernaut
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config, use_karras_sigmas=True
            )
        return self.pipe

    def _get_video_pipe(self):
        if self.video_pipe is None:
            import torch
            from diffusers import DiffusionPipeline
            print("⚡ Carregando Wan 2.1-I2V (14B)... Isso pode levar um momento.")
            
            load_path = self.video_path if os.path.exists(self.video_path) else "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"
            
            # Carrega o modelo Wan 2.1
            self.video_pipe = DiffusionPipeline.from_pretrained(
                load_path, 
                torch_dtype=torch.bfloat16,
                local_files_only=os.path.exists(self.video_path)
            )
            
            # Wan 2.1 14B é gigante (28GB+). Usamos offload para sobrar VRAM para o processamento.
            self.video_pipe.enable_model_cpu_offload()
            
            print("✅ Wan 2.1-I2V carregado com sucesso!")
        return self.video_pipe

    def _get_inpaint_pipe(self):
        if self.inpaint_pipe is None:
            import torch
            from diffusers import StableDiffusionXLInpaintPipeline
            if not os.path.exists(self.inpaint_path):
                raise Exception("Erro: Modelo Inpaint não encontrado no Volume.")
                
            print("⚡ Carregando Inpaint...")
            self.inpaint_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
                self.inpaint_path, torch_dtype=torch.float16, local_files_only=True
            )
            self.inpaint_pipe.enable_model_cpu_offload()
            self.inpaint_pipe.enable_xformers_memory_efficient_attention()
        return self.inpaint_pipe

    def _get_face_app(self):
        if self.face_app is None:
            import insightface
            from insightface.app import FaceAnalysis
            print("👤 Carregando Face Engine (InsightFace)...")
            self.face_app = FaceAnalysis(name="buffalo_l", providers=['CUDAExecutionProvider'])
            self.face_app.prepare(ctx_id=0, det_size=(640, 640))
        return self.face_app

    def _get_face_swapper(self):
        if self.face_swapper is None:
            import insightface
            print("👤 Carregando Face Swapper (InSwapper)...")
            self.face_swapper = insightface.model_zoo.get_model(self.inswapper_path, download=False)
        return self.face_swapper

    @modal.method()
    def describe_image(self, image_b64: str) -> str:
        """Usa o HelperEngine na nuvem para poupar a VRAM da A100."""
        helper = HelperEngine()
        return helper.describe_image.remote(image_b64)

    @modal.method()
    def refine_prompt(self, prompt: str, context: str = "") -> str:
        """Usa o HelperEngine na nuvem para poupar a VRAM da A100."""
        helper = HelperEngine()
        return helper.refine_prompt.remote(prompt, context)

    @modal.method()
    def generate(self, prompt: str, face_img_base64: str = None) -> str:
        import cv2
        import numpy as np
        import base64
        from PIL import Image
        from io import BytesIO

        def pil_to_b64(img):
            buf = BytesIO()
            # Compressão WebP para reduzir tamanho sem perder qualidade visível
            img.save(buf, format="WEBP", quality=85)
            return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        def b64_to_pil(s):
            if "base64," in s:
                s = s.split("base64,")[1]
            return Image.open(BytesIO(base64.b64decode(s)))

        print(f"🎨 Gerando imagem Realista...")
        
        # ── Liberar VRAM de modelos de vídeo/inpaint antes de gerar imagem ──
        import torch, gc
        if self.video_pipe is not None:
            del self.video_pipe
            self.video_pipe = None
        if self.inpaint_pipe is not None:
            del self.inpaint_pipe
            self.inpaint_pipe = None
        torch.cuda.empty_cache()
        gc.collect()
        
        # ── Google Translate (vocabulário completo da língua portuguesa) ──
        translated = self._translate(prompt)
        print(f"🔄 Google Translate: {translated}")
        
        # Tenta refinar com Brain AI se disponível (opcional)
        try:
            refined = self.refine_prompt(translated)
            print(f"🧠 Brain Refined: {refined}")
        except Exception as brain_err:
            print(f"⚠️ Brain AI indisponível, usando Google Translate direto")
            refined = translated

        pipe = self._get_pipe()
        positive_prompt = f"score_9, score_8_up, score_7_up, {refined}, high quality, cinematic"
        negative_prompt = "cartoon, anime, 3d, render, illustration, low quality, bad quality, blurry, distorted, lowres, text, watermark, bad anatomy, deformed"

        image = pipe(
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=25, # Reduzido de 35 para 25 para mais velocidade
            guidance_scale=7.0, # Ajuste leve
            width=1024,
            height=1024,
        ).images[0]

        # Se houver uma imagem de rosto para FaceSwap
        if face_img_base64:
            print("👤 Aplicando FaceSwap...")
            import numpy as np
            import cv2
            from PIL import Image

            def pil_to_cv2(pil_image):
                return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            def cv2_to_pil(cv2_image):
                return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))

            app = self._get_face_app()
            swapper = self._get_face_swapper()
            
            target_img = pil_to_cv2(image)
            source_img = pil_to_cv2(b64_to_pil(face_img_base64))
            
            source_faces = app.get(source_img)
            target_faces = app.get(target_img)
            
            if source_faces and target_faces:
                source_face = source_faces[0]
                for face in target_faces:
                    target_img = swapper.get(target_img, face, source_face, paste_back=True)
                image = cv2_to_pil(target_img)
            else:
                print("⚠️ Nenhum rosto detectado para FaceSwap.")

        buf = BytesIO()
        image.save(buf, format="WEBP", quality=85)
        return save_output_file(buf.getvalue(), "webp")

    @modal.method()
    def inpaint(self, image_b64: str, mask_b64: str, prompt: str) -> str:
        import base64
        from PIL import Image
        from io import BytesIO

        def b64_to_pil(s):
            if "base64," in s:
                s = s.split("base64,")[1]
            return Image.open(BytesIO(base64.b64decode(s)))

        def pil_to_b64(img):
            buf = BytesIO()
            # Compressão WebP para reduzir tamanho sem perder qualidade visível
            img.save(buf, format="WEBP", quality=85)
            return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        inpaint_pipe = self._get_inpaint_pipe()
        
        import torch, gc
        if self.video_pipe is not None:
            del self.video_pipe
            self.video_pipe = None
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
        if self.brain_model is not None:
            del self.brain_model
            self.brain_model = None
        torch.cuda.empty_cache()
        gc.collect()
        output = inpaint_pipe(
            prompt=prompt,
            image=b64_to_pil(image_b64).convert("RGB"),
            mask_image=b64_to_pil(mask_b64).convert("L"),
        ).images[0]

        buf = BytesIO()
        output.save(buf, format="WEBP", quality=85)
        return save_output_file(buf.getvalue(), "webp")

    @modal.method()
    def ping(self):
        return "pong"

    @modal.method()
    def animate(self, image_b64: str, prompt: str = "", face_img_b64: str = None, width: int = 704, height: int = 480, motion_intensity: str = "normal") -> str:
        """Transforma uma imagem em vídeo 5s. Aceita prompt de movimento e faceswap."""
        # Força call_id para string para evitar erros de tipo
        try:
            call_id = str(modal.current_input_id())
        except:
            call_id = "unknown_task"

        # Log físico no volume para debug de cold start
        try:
            with open("/models/debug_log.txt", "a") as f:
                import datetime
                f.write(f"{datetime.datetime.now()} - Animate started - ID: {call_id}\n")
        except:
            pass

        def log_step(msg: str):
            clean_msg = str(msg)
            print(f"[{call_id}] {clean_msg}")
            try:
                if call_id != "unknown_task":
                    # Usa uma lista local para evitar problemas de concorrência com o Dict do Modal
                    logs = job_logs.get(call_id, [])
                    logs.append(clean_msg)
                    job_logs[call_id] = logs
            except:
                pass

        print(f"DEBUG: animate call started for call_id={call_id}")
        try:
            log_step("🚀 Servidor da IA iniciou: preparando container (isso pode levar ~2min no primeiro uso).")
            print("DEBUG: log_step 1 finished")
            import torch
            import base64
            import os
            from PIL import Image
            from io import BytesIO
            import tempfile
            import subprocess
            import numpy as np
            import cv2

            def b64_to_pil(s):
                if "base64," in s: s = s.split("base64,")[1]
                # Remove espaços, quebras de linha e garante que seja ASCII puro
                s_clean = "".join(s.split()).encode("ascii", errors="ignore")
                return Image.open(BytesIO(base64.b64decode(s_clean))).convert("RGB")

            def pil_to_cv2(pil_img):
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            def cv2_to_pil(cv2_img):
                return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))

            # ── DICIONÁRIO DE AÇÕES GROK007 (MASSIVO & SEM CENSURA) ──
            # Mapeia termos para intensidade (1-255). 
            # Valores altos = Movimento explosivo | Valores baixos = Preservação de detalhes.
            MOTION_MAP = {
                # --- Movimentos Básicos ---
                "olhar": 20, "look": 20, "encara": 25, "stare": 25, "blink": 20, "pisca": 20,
                "falar": 40, "talk": 40, "cantar": 45, "sing": 45, "sorrir": 30, "smile": 30,
                "caminhar": 50, "walk": 50, "andar": 50, "slow motion": 30,
            
                # --- Ações de Corpo Inteiro ---
                "correr": 100, "run": 100, "pular": 110, "jump": 110, "dançar": 85, "dance": 85,
                "sentar": 60, "sit": 60, "levantar": 65, "get up": 65, "agachar": 70, "squat": 70,
                "cair": 90, "fall": 90, "girar": 80, "spin": 80, "rodar": 80,
            
                # --- Ações de Vestuário & Interação ---
                "tirar a roupa": 110, "undress": 110, "tirar a camisa": 100, "take off shirt": 100,
                "striptease": 115, "nua": 90, "nude": 90, "pelada": 90, "naked": 90,
                "vestir": 80, "puxar": 75, "pull": 75, "empurrar": 80, "push": 80,
            
                # --- DICIONÁRIO EXPLÍCITO / PORNOGRÁFICO (SOLICITADO) ---
                "sexo": 130, "sex": 130, "foder": 140, "fuck": 140, "comer": 135,
                "masturbação": 120, "masturbating": 120, "punheta": 120, "siririca": 120,
                "boquete": 100, "blowjob": 100, "chupar": 95, "suck": 95,
                "gemer": 40, "moan": 40, "orgasmo": 110, "orgasm": 110,
                "penitration": 145, "penetração": 145, "anal": 130, "vaginal": 130,
                "doggystyle": 135, " missionary": 110, "cowgirl": 140,
                "ejaculação": 150, "cum": 150, "gozar": 150, "jato": 160,
                "beijar": 50, "kiss": 50, "lambendo": 60, "licking": 60,
                "peitos": 70, "breasts": 70, "bunda": 80, "ass": 80, "pau": 90, "dick": 90,
                "buceta": 90, "pussy": 90, "hardcore": 160, "gangbang": 170,
            }
        
            prompt_lower = prompt.lower()
            motion_bucket = 40  # Valor base seguro
            noise_level = 0.01  # Ruído base (fidelidade alta)

            # Detecta a ação e ajusta o motor
            for keyword, bucket in MOTION_MAP.items():
                if keyword in prompt_lower:
                    motion_bucket = bucket
                    # Se for uma ação complexa (sentar, tirar roupa, sexo), 
                    # aumentamos o noise para a IA conseguir redesenhar a pose.
                    if bucket > 60:
                        noise_level = 0.05
                    if bucket > 120:
                        noise_level = 0.08 # Ações extremas precisam de mais "liberdade" criativa
                    break

            print(f"🎬 Motor de Ação | Bucket: {motion_bucket} | Noise: {noise_level}")

            # Ajuste dinâmico baseado na intensidade da ação
            # Se a ação for muito intensa, aumentamos a orientação (guidance) para não derreter
            dynamic_guidance = 4.5
            if motion_bucket > 100:
                dynamic_guidance = 6.0 # Força a IA a manter a forma em ações rápidas
            elif motion_bucket < 40:
                dynamic_guidance = 3.5 # Permite movimentos mais sutis e naturais

            # ── FaceSwap na imagem de entrada (se fornecida) ──
            # LTX-Video precisa de dimensões divisíveis por 32
            base_pil = b64_to_pil(image_b64).resize((width, height))
            if face_img_b64:
                print("👤 Aplicando FaceSwap antes da animação...")
                try:
                    app    = self._get_face_app()
                    swapper = self._get_face_swapper()
                    target_cv = pil_to_cv2(base_pil)
                    source_cv = pil_to_cv2(b64_to_pil(face_img_b64))
                    src_faces = app.get(source_cv)
                    tgt_faces = app.get(target_cv)
                    if src_faces and tgt_faces:
                        for face in tgt_faces:
                            target_cv = swapper.get(target_cv, face, src_faces[0], paste_back=True)
                        base_pil = cv2_to_pil(target_cv)
                        print("✅ FaceSwap aplicado.")
                    else:
                        print("⚠️ Rosto não detectado — animando sem faceswap.")
                except Exception as fe:
                    print(f"⚠️ FaceSwap erro: {fe}")

            # ── Liberar VRAM de outros modelos de forma agressiva ──
            log_step("🧹 Limpando VRAM para o motor Wan 2.1 14B...")
            models_to_del = ['pipe', 'face_app', 'face_swapper']
            for model_attr in models_to_del:
                if hasattr(self, model_attr) and getattr(self, model_attr) is not None:
                    delattr(self, model_attr)
                    setattr(self, model_attr, None)
            
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            
            # ── Gerar vídeo com Wan 2.1 (O Estado da Arte) ──
            log_step("⚙️ Ativando motor Wan 2.1 (Tecnologia de elite)...")
            pipe = self._get_video_pipe()
        
            log_step("🧠 Cérebro Wan traduzindo intenção em deslocamento 3D...")
            try:
                helper = HelperEngine()
                img_desc = helper.describe_image.remote(image_b64)
                refined_motion = helper.refine_prompt.remote(prompt, context=img_desc)
                log_step(f"🎯 Roteiro de Ação: '{refined_motion}'")
            except Exception as brain_err:
                log_step(f"⚠️ Cérebro instável, usando tradução padrão.")
                refined_motion = self._translate(prompt)

            # Configuração dinâmica de passos, escala de orientação (guidance) e amplificadores de movimento
            if motion_intensity == "low":
                num_steps = 15
                guidance_scale = 4.5
                refined_motion = f"subtle gentle movement, slow motion, slow panning, {refined_motion}"
            elif motion_intensity == "high":
                num_steps = 20
                guidance_scale = 8.0
                refined_motion = f"highly dynamic motion, fast action, expressive movement, {refined_motion}"
            elif motion_intensity == "extreme":
                num_steps = 25
                guidance_scale = 10.0
                refined_motion = f"extremely fast and explosive action, dramatic physical movement, hyper dynamic motion, {refined_motion}"
            else: # "normal"
                num_steps = 20
                guidance_scale = 6.0

            log_step(f"🎬 Wan 2.1 iniciando geração (Passos: {num_steps}, Guidance: {guidance_scale}, Frames: 49)...")
            torch.cuda.empty_cache()
            
            video_generate = pipe(
                prompt=refined_motion,
                negative_prompt="worst quality, low quality, blurry, distorted, deformed, static, still, inconsistent motion, weird anatomy",
                image=base_pil,
                num_frames=49, 
                num_inference_steps=num_steps,
                guidance_scale=guidance_scale,
                output_type="pil",
                generator=torch.Generator(device="cuda").manual_seed(int(time.time()))
            ).frames[0]

            log_step("✅ Frames Wan gerados. Compilando...")

            with tempfile.TemporaryDirectory() as tmpdir:
                for i, frame in enumerate(video_generate):
                    frame_720 = frame.resize((1280, 720), Image.LANCZOS)
                    frame_720.save(os.path.join(tmpdir, f"frame_{i:04d}.png"))
            
                output_path = os.path.join(tmpdir, "output.mp4")
            
                subprocess.run([
                    "ffmpeg", "-y",
                    "-framerate", "24", 
                    "-i", os.path.join(tmpdir, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", "-preset", "slow",
                    output_path
                ], check=True, capture_output=True)
            
                with open(output_path, "rb") as f:
                    video_bytes = f.read()
                relative_path = save_output_file(video_bytes, "mp4")
                log_step("🎉 Tudo pronto! Enviando vídeo concluído para o painel.")
                return relative_path

        except Exception as e:
            log_step(f"❌ FALHA CRÍTICA: {str(e)}")
            raise e


@app.function(image=image, memory=1024, timeout=1200, volumes={MODEL_DIR: volume})
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI, Form
    from fastapi.middleware.cors import CORSMiddleware

    web_app = FastAPI(title="GROK007 Engine")
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @web_app.get("/")
    async def health():
        return {"status": "GROK007 Engine Online 🚀"}

    @web_app.get("/outputs/{filename}")
    async def get_output(filename: str):
        import os
        from fastapi.responses import FileResponse
        from fastapi import HTTPException
        
        try:
            volume.reload()
        except Exception as reload_err:
            print(f"⚠️ Erro ao recarregar volume: {reload_err}")
            
        file_path = os.path.join(MODEL_DIR, "outputs", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado no volume.")
        return FileResponse(file_path, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        })

    @web_app.post("/api/generate")
    async def generate_endpoint(prompt: str = Form(...), face_img: str = Form(None)):
        print(f"📥 Recebido pedido de geração: {prompt[:30]}")
        try:
            engine = GrokEngine()
            result = await engine.generate.remote.aio(prompt, face_img)
            print("✅ Geração concluída com sucesso!")
            return {"status": "success", "image": result}
        except Exception as e:
            print(f"❌ Erro na geração: {str(e)}")
            return {"status": "error", "message": str(e)}

    @web_app.post("/api/inpaint")
    async def inpaint_endpoint(
        image: str = Form(...),
        mask: str = Form(...),
        prompt: str = Form(...),
    ):
        engine = GrokEngine()
        result = await engine.inpaint.remote.aio(image, mask, prompt)
        return {"status": "success", "image": result}

    @web_app.post("/api/refine")
    async def refine_endpoint(prompt: str = Form(...)):
        """Acesso direto ao Cérebro para ver o prompt expandido."""
        try:
            helper = HelperEngine()
            result = await helper.refine_prompt.remote.aio(prompt)
            return {"status": "success", "refined": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    from pydantic import BaseModel
    from typing import Optional

    class AnimateRequest(BaseModel):
        image: str
        prompt: Optional[str] = ""
        face_img: Optional[str] = None
        width: Optional[int] = 704
        height: Optional[int] = 480
        motion_intensity: Optional[str] = "normal"

    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    @web_app.post("/api/animate/start")
    async def animate_start_endpoint(req: AnimateRequest):
        """Inicia a geração de vídeo e retorna um job_id (Polling)."""
        try:
            prompt_text = (req.prompt or "cinematic motion").strip()
            engine = GrokEngine()
            
            call = engine.animate.spawn(
                image_b64=req.image, 
                prompt=prompt_text, 
                face_img_b64=req.face_img,
                width=req.width,
                height=req.height,
                motion_intensity=req.motion_intensity or "normal"
            )
            # Inicializa os logs
            job_logs[call.object_id] = ["📡 Servidor recebeu a requisição. Aguardando a IA iniciar (Cold start pode levar 2-3 min)..."]
            
            return {"status": "processing", "job_id": call.object_id}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao iniciar IA: {str(e)}"}

    @web_app.get("/api/animate/status")
    async def animate_status_endpoint(job_id: str):
        """Retorna o status do vídeo e os logs detalhados (Polling)."""
        try:
            from modal.functions import FunctionCall
            call = FunctionCall.from_id(job_id)
            
            # Pega os logs atuais
            current_logs = job_logs.get(job_id, ["📡 Aguardando logs..."])

            try:
                # timeout=0 testa se já acabou
                result = call.get(timeout=0)
                current_logs.append("✅ Vídeo finalizado com sucesso!")
                return {"status": "success", "video": result, "logs": current_logs}
            except TimeoutError:
                return {"status": "processing", "logs": current_logs}
            except Exception as e:
                current_logs.append(f"❌ Falha interna: {str(e)}")
                return {"status": "error", "message": str(e), "logs": current_logs}
        except Exception as e:
            return {"status": "error", "message": f"Job não encontrado ou expirado: {str(e)}"}

    @web_app.get("/api/upload-test")
    async def upload_test():
        """Endpoint para testar se o backend aceita uploads."""
        return {"status": "ok", "upload": True, "message": "Backend pronto para uploads ✅"}

    return web_app
