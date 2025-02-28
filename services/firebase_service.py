import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# ✅ Inicializar Firebase apenas se ainda não estiver inicializado
if not firebase_admin._apps:
    try:
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
        if not firebase_credentials:
            raise ValueError("❌ Credenciais do Firebase não encontradas!")

        cred_info = json.loads(firebase_credentials)
        cred = credentials.Certificate(cred_info)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase inicializado com sucesso!")

    except Exception as e:
        raise ValueError(f"❌ Erro ao inicializar o Firebase: {e}")

# ✅ Conectar ao Firestore
db = firestore.client()

# ✅ Função genérica para salvar um documento em qualquer coleção
def salvar_dados(colecao, dados):
    try:
        db.collection(colecao).add(dados)
        print(f"✅ Dados salvos com sucesso na coleção '{colecao}'!")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados na coleção '{colecao}': {e}")
        return False

# ✅ Função genérica para buscar todos os documentos de uma coleção
def buscar_dados(colecao):
    try:
        docs = db.collection(colecao).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"❌ Erro ao buscar dados na coleção '{colecao}': {e}")
        return []

# ✅ Função genérica para deletar todos os documentos de uma coleção
def limpar_colecao(colecao):
    try:
        docs = db.collection(colecao).stream()
        for doc in docs:
            db.collection(colecao).document(doc.id).delete()
        print(f"✅ Todos os documentos da coleção '{colecao}' foram removidos!")
        return True
    except Exception as e:
        print(f"❌ Erro ao limpar a coleção '{colecao}': {e}")
        return False
