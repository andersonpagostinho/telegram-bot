#!/usr/bin/env python3
import json
import os

cred_file = 'firebase_credentials.json'
if os.path.exists(cred_file):
    with open(cred_file) as f:
        creds = json.load(f)
    print(f"Project ID: {creds.get('project_id', 'NÃO ENCONTRADO')}")
    print(f"Type: {creds.get('type', 'NÃO ENCONTRADO')}")
else:
    print("Arquivo de credenciais não encontrado")
