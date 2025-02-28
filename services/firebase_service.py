import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Pegar credenciais do Firebase
firebase_json_path = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_path or not os.path.exists(firebase_json_path):
    raise ValueError("❌ Arquivo de credenciais do Firebase não encontrado!")

cred = credentials.Certificate(firebase_json_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Função para salvar uma nova tarefa no Firestore
def salvar_tarefa(descricao):
    try:
        tarefa_ref = db.collection("Tarefas").document()
        tarefa_ref.set({"descricao": descricao, "status": "pendente"})
        return True
    except Exception as e:
        print(f"Erro ao salvar tarefa: {e}")
        return False
