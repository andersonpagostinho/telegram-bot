import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# 🔥 Pegando as credenciais do Firebase da variável de ambiente (Render)
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

# Converter string JSON para um dicionário Python
cred_info = json.loads(firebase_credentials)

# Inicializa o Firebase apenas se ainda não estiver inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()

# Testar criando um documento no Firestore
doc_ref = db.collection("testes").document("primeiro_teste")
doc_ref.set({"mensagem": "Conexão bem-sucedida no Render!"})

# Buscar o documento salvo
doc = doc_ref.get()
if doc.exists:
    print(f"✅ Firebase conectado e dados enviados com sucesso! Mensagem: {doc.to_dict()}")
else:
    print("❌ Erro: O documento não foi salvo corretamente!")
