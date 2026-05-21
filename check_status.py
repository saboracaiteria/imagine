import urllib.request
import json
import time
import sys

job_id = sys.argv[1] if len(sys.argv) > 1 else "fc-01KRRF9CE53AFDZ16AGR25C0AB"
url = f'https://ribeiro-022587--grok007-engine-fastapi-app.modal.run/api/animate/status?job_id={job_id}'

print(f"Monitoring Job: {job_id}")

while True:
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            status = data.get("status")
            logs = data.get("logs", [])
            
            # Print new logs
            for log in logs[-5:]: # Show last 5 logs
                safe_log = log.encode('ascii', 'replace').decode('ascii')
                print(f">> {safe_log}")
            
            if status == "success":
                print("\nFinalizado!")
                break
            elif status == "error":
                print(f"\nErro: {data.get('message')}")
                break
            else:
                print(f"Status: {status}... aguardando 10s")
    except Exception as e:
        print('Error:', str(e))
    
    time.sleep(10)
