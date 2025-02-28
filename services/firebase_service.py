import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# 🔥 Verifica a variável de ambiente
firebase_json_path = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_path or not os.path.exists(firebase_json_path):
    raise ValueError(f"❌ Arquivo de credenciais do Firebase não encontrado! Caminho: {firebase_json_path}")

# ✅ Carregar credenciais do Firebase corretamente
with open(firebase_json_path, "r") as f:
    cred_info = json.load(f)

cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Função para salvar tarefa no Firestore
def salvar_tarefa(descricao):
    doc_ref = db.collection("Tarefas").document()
    doc_ref.set({"descricao": descricao, "prioridade": "baixa"})
    print(f"✅ Tarefa '{descricao}' salva com sucesso no Firestore!")
