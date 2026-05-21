import urllib.request
import urllib.parse
import json

print('Iniciando requisição para gerar a primeira imagem...')
url = 'https://ribeiro-022587--grok007-engine-fastapi-app.modal.run/api/generate'
data = urllib.parse.urlencode({'prompt': 'a futuristic cyberpunk warrior, highly detailed, neon lights, 4k'}).encode('utf-8')

try:
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=600) as response:
        print('Status Code:', response.getcode())
        if response.getcode() == 200:
            print('SUCESSO! O modelo foi baixado, carregado e a imagem gerada.')
except urllib.error.URLError as e:
    print('Falha na requisição:', str(e))
except Exception as e:
    print('Erro genérico:', str(e))
