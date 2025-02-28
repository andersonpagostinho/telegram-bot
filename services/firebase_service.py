import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# ✅ Verifica se o Firebase já está inicializado para evitar erro
if not firebase_admin._apps:
    try:
        # ✅ Obtém as credenciais do Firebase do ambiente (Render)
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
        if not firebase_credentials:
            raise ValueError("❌ Credenciais do Firebase não encontradas!")

        # ✅ Converte a string JSON armazenada na variável de ambiente para um dicionário
        cred_info = json.loads(firebase_credentials)

        # ✅ Inicializa o Firebase com as credenciais carregadas
        cred = credentials.Certificate(cred_info)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase inicializado com sucesso!")

    except Exception as e:
        raise ValueError(f"❌ Erro ao inicializar o Firebase: {e}")

# ✅ Conectar ao Firestore
db = firestore.client()

# ✅ Função para salvar uma tarefa no Firestore
def salvar_tarefa(descricao):
    try:
        doc_ref = db.collection("Tarefas").document()
        doc_ref.set({"descricao": descricao, "prioridade": "baixa"})  # Padrão: prioridade baixa
        print(f"✅ Tarefa '{descricao}' salva no Firestore!")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar tarefa: {e}")
        return False

# ✅ Função para buscar todas as tarefas do Firestore
def buscar_tarefas():
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        tarefas = [{"id": doc.id, **doc.to_dict()} for doc in tarefas_ref]
        return tarefas
    except Exception as e:
        print(f"❌ Erro ao buscar tarefas: {e}")
        return []

# ✅ Função para limpar todas as tarefas no Firestore
def limpar_tarefas():
    try:
        tarefas_ref = db.collection("Tarefas").stream()
        for doc in tarefas_ref:
            db.collection("Tarefas").document(doc.id).delete()
        print("✅ Todas as tarefas foram removidas do Firestore!")
        return True
    except Exception as e:
        print(f"❌ Erro ao limpar tarefas: {e}")
        return False
