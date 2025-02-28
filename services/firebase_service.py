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

# ✅ Função para salvar dados em uma coleção
def salvar_dados(colecao, dados):
    try:
        doc_ref = db.collection(colecao).add(dados)
        print(f"✅ Dados salvos em '{colecao}' com sucesso!")
        return doc_ref
    except Exception as e:
        print(f"❌ Erro ao salvar dados em '{colecao}': {e}")
        return None

# ✅ Função para buscar dados de uma coleção
def buscar_dados(colecao):
    try:
        docs = db.collection(colecao).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"❌ Erro ao buscar dados de '{colecao}': {e}")
        return []

# ✅ Função para deletar todos os documentos de uma coleção
def deletar_colecao(colecao):
    try:
        docs = db.collection(colecao).stream()
        for doc in docs:
            doc.reference.delete()
        print(f"🗑️ Coleção '{colecao}' deletada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao deletar coleção '{colecao}': {e}")
