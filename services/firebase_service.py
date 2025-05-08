import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime, timedelta  # 🔹 Adicionado para salvar_cliente funcionar corretamente

# ✅ Carregar credenciais do Firebase diretamente da variável de ambiente
# 🔹 Primeiro, tentamos carregar a variável de ambiente (Render)
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

# 🔹 Se estiver rodando localmente e não houver variável de ambiente, usamos o arquivo JSON
if not firebase_credentials and os.path.exists("firebase_credentials.json"):
    with open("firebase_credentials.json") as f:
        firebase_credentials = json.load(f)
else:
    try:
        # Corrige aspas e quebras de linha, se necessário
        firebase_credentials = firebase_credentials.replace('\\"', '"').replace('\\\\n', '\\n')
        firebase_credentials = json.loads(firebase_credentials)
    except Exception as e:
        raise ValueError(f"❌ Erro ao carregar credenciais do Firebase: {e}")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

# 🔹 Inicializar Firebase APENAS se ainda não estiver rodando
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase inicializado com sucesso!")
else:
    print("⚠️ Firebase já estava inicializado!")

# 🔹 Conectar ao Firestore
db = firestore.client()

# ✅ Função genérica para salvar um documento em qualquer coleção
def salvar_dados(colecao, dados):
    try:
        print(f"📌 Tentando salvar na coleção: {colecao}")
        print(f"📌 Dados a serem salvos: {dados}")

        ref = db.collection(colecao).document()  # Criando um documento único
        ref.set(dados)  # Salvando os dados
        
        print(f"✅ Dados salvos com sucesso na coleção '{colecao}'!")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados na coleção '{colecao}': {e}")
        return False

# ✅ Salvar ou atualizar dados de um cliente
def salvar_cliente(user_id, dados):
    try:
        dados_padrao = {
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"],
            "dataAssinatura": datetime.now().strftime("%Y-%m-%d"),
            "proximoPagamento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        }

        dados_completos = {**dados_padrao, **dados}  # Prioriza os dados passados
        db.collection("Clientes").document(str(user_id)).set(dados_completos, merge=True)
        print(f"✅ Cliente {user_id} salvo com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar cliente {user_id}: {e}")
        return False

# ✅ Buscar dados de um cliente
def buscar_cliente(user_id):
    try:
        print(f"📌 Buscando dados do usuário {user_id}")  # 🔹 Adicionado para debug
        doc = db.collection("Clientes").document(str(user_id)).get()
        if doc.exists:
            print(f"✅ Dados encontrados: {doc.to_dict()}")  # 🔹 Exibir os dados encontrados
            return doc.to_dict()
        print("❌ Nenhum dado encontrado!")
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar cliente {user_id}: {e}")
        return None

# ✅ Função genérica para buscar todos os documentos de uma coleção
def buscar_dados(colecao):
    try:
        docs = db.collection(colecao).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"❌ Erro ao buscar dados na coleção '{colecao}': {e}")
        return []

def buscar_dado_em_path(path: str):
    try:
        print(f"🔎 [DEBUG] buscando dado em path: {path}")
        doc = db.document(path).get()
        if doc.exists:
            print(f"📥 [DEBUG] Documento encontrado: {doc.to_dict()}")
            return doc.to_dict()
        else:
            print("📭 [DEBUG] Documento não encontrado.")
            return None
    except Exception as e:
        print(f"❌ Erro em buscar_dado_em_path: {e}")
        return None

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

# ✅ Função para salvar dados em caminhos aninhados como: Clientes/{user_id}/Eventos/{event_id}
def salvar_dado_em_path(caminho, dados):
    try:
        print(f"📍 [DEBUG] Salvando em path: {caminho}")
        print(f"📍 [DEBUG] Dados: {dados}")

        partes = caminho.split('/')
        ref = db

        for i in range(len(partes)):
            if i % 2 == 0:  # coleção
                ref = ref.collection(partes[i])
            else:  # documento
                ref = ref.document(partes[i])

        ref.set(dados)
        print(f"✅ Dados salvos em: {caminho}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar no caminho '{caminho}': {e}")
        return False

# ✅ Função para buscar documentos de uma subcoleção
def buscar_subcolecao(caminho):
    try:
        print(f"🔍 [DEBUG] Buscando no caminho: {caminho}")
        partes = caminho.split('/')
        ref = db

        for i in range(len(partes)):
            if i % 2 == 0:
                ref = ref.collection(partes[i])
            else:
                ref = ref.document(partes[i])

        if len(partes) % 2 != 0:  # termina em coleção
            docs = ref.stream()
            resultados = {doc.id: doc.to_dict() for doc in docs}
            print(f"🔎 [DEBUG] Documentos encontrados: {list(resultados.keys())}")
            return resultados
        else:
            doc = ref.get()
            if doc.exists:
                print(f"🔎 [DEBUG] Documento encontrado: {doc.id}")
                return doc.to_dict()
            else:
                print("📭 [DEBUG] Documento não encontrado.")
                return None
    except Exception as e:
        print(f"❌ Erro ao buscar dados de: {caminho} | {e}")
        return {}

# ✅ Salva evento simples (caso queira salvar fora da subcoleção)
def salvar_evento(evento_data):
    try:
        db.collection("Eventos").add(evento_data)
        return True
    except Exception as e:
        print(f"Erro ao salvar evento: {e}")
        return False

# ✅ NOVO: Buscar todos os clientes do sistema
def buscar_todos_clientes():
    try:
        print("🔍 Buscando todos os clientes do Firebase...")
        docs = db.collection("Clientes").stream()
        clientes = {doc.id: doc.to_dict() for doc in docs}
        print(f"✅ {len(clientes)} clientes encontrados.")
        return clientes
    except Exception as e:
        print(f"❌ Erro ao buscar todos os clientes: {e}")
        return {}

# ✅ Deletar dados em caminhos aninhados como: Usuarios/{user_id}/FollowUps/{followup_id}
def deletar_dado_em_path(caminho):
    try:
        print(f"🗑️ [DEBUG] Deletando do path: {caminho}")

        partes = caminho.split('/')
        ref = db

        for i in range(len(partes)):
            if i % 2 == 0:  # coleção
                ref = ref.collection(partes[i])
            else:  # documento
                ref = ref.document(partes[i])

        ref.delete()
        print(f"✅ Dado deletado de: {caminho}")
        return True
    except Exception as e:
        print(f"❌ Erro ao deletar no caminho '{caminho}': {e}")
        return False

# ✅ atualizar dados em path
def atualizar_dado_em_path(caminho, dados):
    try:
        print(f"🛠️ [DEBUG] Atualizando (merge) em path: {caminho}")
        print(f"🛠️ [DEBUG] Dados: {dados}")

        partes = caminho.split('/')
        ref = db

        for i in range(len(partes)):
            if i % 2 == 0:  # coleção
                ref = ref.collection(partes[i])
            else:  # documento
                ref = ref.document(partes[i])

        ref.set(dados, merge=True)
        print(f"✅ Dados atualizados com merge em: {caminho}")
        return True
    except Exception as e:
        print(f"❌ Erro ao atualizar (merge) no caminho '{caminho}': {e}")
        return False

