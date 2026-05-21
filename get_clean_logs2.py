import os
import subprocess
import codecs
import time

env = os.environ.copy()
env["PYTHONUTF8"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

print("Starting Modal log stream connection (silent write to file)...")
try:
    process = subprocess.Popen(
        ["modal", "app", "logs", "grok007-engine"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    lines = []
    start_time = time.time()
    while time.time() - start_time < 12: # read for 12 seconds
        if process.poll() is not None:
            break
            
        line = process.stdout.readline()
        if line:
            lines.append(line)
        else:
            time.sleep(0.1)
            
    process.terminate()
    
    with open("modal_logs_utf8.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    print(f"Done! Successfully wrote {len(lines)} log lines to modal_logs_utf8.txt.")
except Exception as e:
    print("Error:", e)
