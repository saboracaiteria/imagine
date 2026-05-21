import os
import subprocess
import codecs

# Use modal CLI but force utf-8 encoding and ignore errors
try:
    process = subprocess.Popen(
        ["modal", "app", "logs", "grok007-engine"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    with codecs.open("modal_logs.txt", "w", encoding="utf-8", errors="replace") as f:
        # Read the first 200 lines to avoid hanging forever
        for i in range(200):
            line = process.stdout.readline()
            if not line:
                break
            f.write(line.decode('utf-8', errors='replace'))
    
    process.terminate()
except Exception as e:
    with open("modal_logs_err.txt", "w") as f:
        f.write(str(e))
