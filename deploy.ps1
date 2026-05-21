$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
modal deploy backend/modal_backend.py 2>&1 | Out-File -Encoding utf8 deploy_log.txt
Get-Content deploy_log.txt
