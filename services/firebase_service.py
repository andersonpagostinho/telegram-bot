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

# Função para salvar dados no Firestore
def salvar_dados(colecao, dados):
    try:
        doc_ref = db.collection(colecao).add(dados)
        print(f"✅ Dados salvos na coleção '{colecao}': {dados}")
        return doc_ref
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")

# Função para buscar todos os documentos de uma coleção
def buscar_dados(colecao):
    try:
        docs = db.collection(colecao).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"❌ Erro ao buscar dados: {e}")
        return []

# Inicializar Firebase
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred)
db = firestore.client()
