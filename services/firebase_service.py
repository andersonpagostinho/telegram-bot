import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Pegar credenciais diretamente da variável de ambiente
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

# Converter a string JSON armazenada na variável de ambiente para um dicionário
cred_info = json.loads(firebase_credentials)

# Inicializar Firebase
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()
