import os
import subprocess

# Force UTF-8 encoding for python and child processes
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    print("Fetching last 50 lines of logs from Modal...")
    # Run modal app logs with tail/lines count if supported, or just grab the latest
    result = subprocess.run(
        ["modal", "app", "logs", "grok007-engine"],
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )
    
    # Save output to modal_logs_utf8.txt
    with open("modal_logs_utf8.txt", "w", encoding="utf-8") as f:
        f.write(result.stdout)
        
    # Also print the last 20 lines to stdout so we can see it here
    lines = result.stdout.splitlines()
    print(f"Total lines retrieved: {len(lines)}")
    for line in lines[-30:]:
        print(line)
        
except Exception as e:
    print("Error during log retrieval:", e)
