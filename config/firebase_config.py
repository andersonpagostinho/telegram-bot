import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# 🔥 Força o carregamento do .env
load_dotenv(override=True)

firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_str:
    raise ValueError("❌ Variável FIREBASE_CREDENTIALS não encontrada!")

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
db = firestore.client()
