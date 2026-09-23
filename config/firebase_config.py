import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# 🔥 Força o carregamento do .env
load_dotenv(override=True)

# [FIX-TRUNCAMENTO] Tentar Base64 primeiro (sem truncamento em variáveis env)
firebase_json_str = None
firebase_creds_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")

if firebase_creds_b64:
    try:
        import base64
        decoded = base64.b64decode(firebase_creds_b64).decode('utf-8')
        firebase_json_str = decoded
        print(f"[OK] FIREBASE_CREDENTIALS carregado de Base64 (config)", flush=True)
    except Exception as e:
        print(f"[WARN] Falha ao decodificar Base64: {str(e)[:100]}", flush=True)
        firebase_json_str = None

# [FALLBACK] Se não conseguiu Base64, tenta variável JSON/caminho normal
if not firebase_json_str:
    firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_str:
    raise ValueError("[ERROR] Nenhuma credencial encontrada! Defina FIREBASE_CREDENTIALS_B64 ou FIREBASE_CREDENTIALS")

# Se a variável for um JSON completo (e não um caminho)
try:
    firebase_json = json.loads(firebase_json_str)
    firebase_json_path = "firebase_credentials.json"

    # Criar um arquivo temporário
    with open(firebase_json_path, "w") as f:
        json.dump(firebase_json, f)

    print(f"✅ Arquivo criado: {firebase_json_path}")

except json.JSONDecodeError:
    firebase_json_path = firebase_json_str  # Assume que é um caminho válido

# Inicializar o Firebase
cred = credentials.Certificate(firebase_json_path)
firebase_admin.initialize_app(cred)
# [INFRA-03] Removido: db = firestore.client() (cliente desnecessário, usar get_db() de firestore_client.py)
