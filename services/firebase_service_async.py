from datetime import datetime, timedelta
from google.cloud.firestore_v1 import AsyncClient
from config.firebase_config import db  # Firebase já inicializado
import os

# ✅ Define a variável de ambiente se ainda não estiver definida
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase_credentials.json"

# ✨ Cliente assíncrono do Firestore
client = AsyncClient()

# 🔁 Utilitário para navegar até o path
def get_ref_from_path(path: str):
    partes = path.split("/")
    ref = client
    for i in range(len(partes)):
        if i % 2 == 0:
            ref = ref.collection(partes[i])
        else:
            ref = ref.document(partes[i])
    return ref

async def verificar_firebase():
    try:
        dados = await buscar_dados("Usuarios")  # ou outro caminho válido
        print("✅ Firebase verificado com sucesso.")
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar Firebase: {e}")
        return False

# ✅ Buscar cliente (documento)
async def buscar_cliente(user_id):
    try:
        doc_ref = client.collection("Clientes").document(str(user_id))
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar cliente: {e}")
        return None

# ✅ Buscar subcoleção (ex: Clientes/{id}/Tarefas)
async def buscar_subcolecao(path: str):
    try:
        ref = get_ref_from_path(path)
        partes = path.split("/")
        resultados = {}

        if len(partes) % 2 == 1:  # subcoleção
            docs = ref.stream()
            async for doc in docs:
                data = doc.to_dict()
                print(f"📄 Documento encontrado em {path}/{doc.id}: {data}")
                resultados[doc.id] = data
        else:
            doc = await ref.get()
            if doc.exists:
                print(f"📄 Documento único em {path}: {doc.to_dict()}")
                resultados = doc.to_dict()
        return resultados
    except Exception as e:
        print(f"❌ Erro ao buscar subcoleção '{path}': {e}")
        return {}

# ✅ Buscar tarefas do usuário
async def buscar_tarefas_do_usuario(user_id: str):
    try:
        path = f"Clientes/{user_id}/Tarefas"
        tarefas = await buscar_subcolecao(path)
        print(f"📋 Tarefas encontradas: {tarefas}")
        return tarefas
    except Exception as e:
        print(f"❌ Erro ao buscar tarefas do usuário {user_id}: {e}")
        return {}

# ✅ Buscar tarefas por descrição
async def buscar_tarefa_por_descricao(user_id: str, descricao: str):
    tarefas = await buscar_tarefas_do_usuario(user_id)
    for id_tarefa, dados in tarefas.items():
        if dados.get("descricao", "").lower() == descricao.lower():
            print(f"✅ Tarefa encontrada: {id_tarefa} -> {dados}")
            return {id_tarefa: dados}
    print("🔍 Nenhuma tarefa encontrada com essa descrição.")
    return {}

# ✅ Salvar dados em path (ex: Clientes/{id}/Eventos/{id})
async def salvar_dado_em_path(path: str, dados: dict):
    try:
        print(f"💾 Tentando salvar dados em: {path}")
        for k, v in dados.items():
            print(f"   - {k}: {v} (tipo: {type(v)})")
        ref = get_ref_from_path(path)
        await ref.set(dados)
        print(f"✅ Dados salvos em: {path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar no caminho '{path}': {e}")
        return False

# ✅ Atualizar dados com merge
async def atualizar_dado_em_path(path: str, dados: dict):
    try:
        ref = get_ref_from_path(path)
        await ref.set(dados, merge=True)
        print(f"✅ Dados atualizados (merge) em: {path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao atualizar (merge) no caminho '{path}': {e}")
        return False

# ✅ Deletar dado por path
async def deletar_dado_em_path(path: str):
    try:
        ref = get_ref_from_path(path)
        await ref.delete()
        print(f"🗑️ Dado deletado de: {path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao deletar no caminho '{path}': {e}")
        return False

# ✅ Limpar coleção inteira
async def limpar_colecao(colecao: str):
    try:
        docs = client.collection(colecao).stream()
        async for doc in docs:
            await client.collection(colecao).document(doc.id).delete()
        print(f"✅ Todos os documentos da coleção '{colecao}' foram removidos!")
        return True
    except Exception as e:
        print(f"❌ Erro ao limpar a coleção '{colecao}': {e}")
        return False

# ✅ Buscar todos os documentos de uma coleção (assíncrono)
async def buscar_dados(colecao: str):
    try:
        docs = client.collection(colecao).stream()
        resultados = [doc.to_dict() async for doc in docs]
        return resultados
    except Exception as e:
        print(f"❌ Erro ao buscar dados da coleção '{colecao}': {e}")
        return []

# ✅ Salvar dados do cliente (com merge)
async def salvar_cliente(user_id: str, dados: dict):
    try:
        ref = client.collection("Clientes").document(user_id)
        await ref.set(dados, merge=True)
        print(f"✅ Cliente {user_id} salvo com sucesso.")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar cliente: {e}")
        return False

# ✅ Salvar dados em uma coleção (gera ID automático)
async def salvar_dados(colecao: str, dados: dict):
    try:
        await client.collection(colecao).add(dados)
        print(f"✅ Documento salvo em '{colecao}' com dados: {dados}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados na coleção '{colecao}': {e}")
        return False

# ✅ Buscar dado em path (documento)
async def buscar_dado_em_path(path: str):
    try:
        ref = get_ref_from_path(path)
        doc = await ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"❌ Erro ao buscar dado em '{path}': {e}")
        return None

# ✅ Buscar todos os clientes (assíncrono)
async def buscar_todos_clientes():
    try:
        docs = client.collection("Clientes").stream()
        resultados = {doc.id: doc.to_dict() async for doc in docs}
        return resultados
    except Exception as e:
        print(f"❌ Erro ao buscar todos os clientes: {e}")
        return {}

# ✅ Salvar evento em coleção global (opcional)
async def salvar_evento(evento_data):
    try:
        await client.collection("Eventos").add(evento_data)
        print("✅ Evento salvo na coleção global.")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar evento global: {e}")
        return False

# ✅ Alias para buscar documento único (para compatibilidade com /start)
async def buscar_documento(path: str):
    return await buscar_dado_em_path(path)

# ✅ Retorna o ID do dono, mesmo se for um cliente
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id

# ✅ Buscar contatos por nome (ex: Clientes/{user_id}/Contatos)
async def buscar_contatos_por_nome(user_id: str, nome: str):
    try:
        path = f"Clientes/{user_id}/Contatos"
        contatos_dict = await buscar_subcolecao(path)

        contatos_filtrados = []
        for id_contato, contato in contatos_dict.items():
            if nome.lower() in contato.get("nome", "").lower():
                contatos_filtrados.append({
                    "id": id_contato,
                    "nome": contato.get("nome"),
                    "email": contato.get("email")
                })

        print(f"🔍 Contatos encontrados para '{nome}': {contatos_filtrados}")
        return contatos_filtrados
    except Exception as e:
        print(f"❌ Erro ao buscar contatos: {e}")
        return []

# ✅ Buscar ID de cliente pelo nome (dentro de um negócio)
async def buscar_id_cliente_por_nome(nome_cliente: str, id_dono: str) -> str | None:
    """
    Procura o ID do cliente com base no nome informado, dentro dos registros do dono.
    """
    nome_normalizado = nome_cliente.strip().lower()
    clientes = await buscar_subcolecao(f"Clientes/{id_dono}/Clientes")
    if not clientes:
        return None

    for uid, dados in clientes.items():
        nome = dados.get("nome", "").strip().lower()
        if nome == nome_normalizado:
            return uid
    return None

