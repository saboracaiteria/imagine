import subprocess
import sys
import os

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

result = subprocess.run(
    [sys.executable, "-m", "modal", "deploy", "backend/modal_backend.py"],
    capture_output=True, encoding="utf-8", errors="replace",
    cwd=r"c:\Users\Terminal\Documents\grok007"
)

with open("deploy_result.txt", "w", encoding="utf-8") as f:
    f.write(f"RETURN CODE: {result.returncode}\n")
    f.write(f"STDOUT:\n{result.stdout}\n")
    f.write(f"STDERR:\n{result.stderr}\n")

print(f"Done. Return code: {result.returncode}")
print("See deploy_result.txt for full output")
