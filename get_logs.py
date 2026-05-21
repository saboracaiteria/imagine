import subprocess
import io

try:
    with io.open("modal_logs.txt", "w", encoding="utf-8") as f:
        subprocess.run(["modal", "app", "logs", "grok007-engine"], stdout=f, stderr=subprocess.STDOUT)
except Exception as e:
    pass
