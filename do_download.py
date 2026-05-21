import subprocess
import sys
import os

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

print("Iniciando download dos modelos Wan 2.1 (14B)...")
print("Isso pode levar de 10 a 20 minutos. Nao feche esta janela.")

result = subprocess.run(
    [sys.executable, "-m", "modal", "run", "backend/modal_backend.py::download_models"],
    capture_output=False, # Show progress in real-time
    encoding="utf-8", 
    errors="replace",
    cwd=r"c:\Users\Terminal\Documents\grok007"
)

print(f"\n✅ Finalizado. Código de retorno: {result.returncode}")
