import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# ✅ Pega as credenciais do Firebase da variável de ambiente no Render
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

try:
    # ✅ Converte a string JSON armazenada na variável de ambiente para um dicionário
    cred_info = json.loads(firebase_credentials)
    
    # ✅ Inicializa o Firebase com as credenciais carregadas
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase inicializado com sucesso!")
except Exception as e:
    raise ValueError(f"❌ Erro ao carregar credenciais do Firebase: {e}")

# ✅ Função para salvar uma tarefa no Firestore
def salvar_tarefa(descricao):
    doc_ref = db.collection("Tarefas").document()
    doc_ref.set({"descricao": descricao, "prioridade": "baixa"})
    print(f"✅ Tarefa '{descricao}' salva com sucesso no Firestore!")
