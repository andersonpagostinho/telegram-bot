from datetime import datetime, timedelta
from google.cloud.firestore_v1 import AsyncClient
from google.oauth2 import service_account
from google.cloud import firestore as fs
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# ============================================================================
# [INIT] Inicializar cliente Firestore com credenciais (padrão backup)
# ============================================================================

PROJECT_ID = "projeto-agente-inteligente"

# [PRODUCAO] Ler credenciais de variável de ambiente
firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_json_str:
    raise ValueError("[ERROR] Variavel FIREBASE_CREDENTIALS nao encontrada!")

firebase_json_path = None

# Estratégia 1: Verificar se é um JSON (começa com {)
if firebase_json_str.strip().startswith("{"):
    try:
        firebase_json = json.loads(firebase_json_str)
        firebase_json_path = "firebase_credentials.json"

        # Criar um arquivo temporário
        with open(firebase_json_path, "w") as f:
            json.dump(firebase_json, f)

        print(f"[OK] Arquivo Firebase criado como JSON: {firebase_json_path}", flush=True)

    except (json.JSONDecodeError, Exception) as e:
        print(f"[WARN] Falha ao fazer parse de JSON: {type(e).__name__}: {str(e)[:100]}", flush=True)
        # Se falhou, não tentar mais como JSON
        firebase_json_path = None
else:
    # Estratégia 2: É um caminho de arquivo (não começa com {)
    firebase_json_path = firebase_json_str
    print(f"[INFO] Variavel FIREBASE_CREDENTIALS parece ser um caminho", flush=True)

# Estratégia 3: Se ainda não temos path, tentar resolver como arquivo no projeto
if not firebase_json_path:
    # Tentar como arquivo no diretório do projeto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_path = os.path.join(project_root, "firebase_credentials.json")

    if os.path.exists(default_path):
        firebase_json_path = default_path
        print(f"[INFO] Usando arquivo padrao do projeto: {firebase_json_path}", flush=True)
    else:
        raise FileNotFoundError(f"[ERROR] Nao foi possivel encontrar credenciais Firebase")

# Estratégia 4: Resolver caminho relativo se necessário
if not os.path.isabs(firebase_json_path):
    if not os.path.exists(firebase_json_path):
        # Tenta no diretório do projeto (pai de services/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        firebase_json_path = os.path.join(project_root, os.path.basename(firebase_json_str))
        print(f"[INFO] Resolvendo caminho relativo: {firebase_json_path}", flush=True)

if not os.path.exists(firebase_json_path):
    raise FileNotFoundError(f"[ERROR] Arquivo Firebase nao encontrado: {firebase_json_path}")

print(f"[OK] Arquivo Firebase validado: {firebase_json_path}", flush=True)

# Validar que temos um caminho válido
if not firebase_json_path or not os.path.exists(firebase_json_path):
    raise FileNotFoundError(f"[ERROR] Arquivo Firebase nao encontrado: {firebase_json_path}")

# [FIX-ASYNC] Definir GOOGLE_APPLICATION_CREDENTIALS para que AsyncClient() encontre credenciais
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = firebase_json_path
    print(f"[INFO] GOOGLE_APPLICATION_CREDENTIALS definido: {firebase_json_path}", flush=True)

# Inicializar o Firebase Admin SDK (para funções que precisam de contexto admin)
try:
    cred = credentials.Certificate(firebase_json_path)
    firebase_admin.initialize_app(cred)
except ValueError:
    # Firebase já inicializado em outro lugar
    pass

# [FIX-ASYNC] Usar AsyncClient em vez de firestore.client() (sync)
# AsyncClient() usa GOOGLE_APPLICATION_CREDENTIALS que acabamos de definir
client = AsyncClient()
print(f"[OK] Firestore inicializado com sucesso!", flush=True)

# [LOOP] Utilitário para navegar até o path
def get_ref_from_path(path: str):
    partes = path.split("/")
    ref = client
    for i in range(len(partes)):
        if i % 2 == 0:
            ref = ref.collection(partes[i])
        else:
            ref = ref.document(partes[i])
    return ref

async def buscar_notificacoes_pendentes(user_id: str):
    """
    Busca apenas notificações ainda não avisadas.
    O status continua sendo validado no scheduler.
    """
    try:
        ref = (
            client.collection("Clientes")
            .document(str(user_id))
            .collection("NotificacoesAgendadas")
        )

        query = ref.where("avisado", "==", False)

        docs = query.stream()
        resultado = {}

        async for doc in docs:
            resultado[doc.id] = doc.to_dict()

        return resultado

    except Exception as e:
        print(f"[ERRO] buscar_notificacoes_pendentes erro: {e}", flush=True)
        return {}

async def verificar_firebase():
    try:
        dados = await buscar_dados("Usuarios")  # ou outro caminho válido
        print("[OK] Firebase verificado com sucesso.")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao verificar Firebase: {e}")
        return False

# [OK] Buscar cliente (documento)
async def buscar_cliente(user_id):
    try:
        doc_ref = client.collection("Clientes").document(str(user_id))
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"[ERRO] Erro ao buscar cliente: {e}")
        return None

# [OK] Buscar subcoleção (ex: Clientes/{id}/Tarefas)
async def buscar_subcolecao(path: str):
    try:
        ref = get_ref_from_path(path)
        partes = path.split("/")
        resultados = {}

        if len(partes) % 2 == 1:  # subcoleção
            docs = ref.stream()
            async for doc in docs:
                data = doc.to_dict()
                print(f"[DOC] Documento encontrado em {path}/{doc.id}: {data}")
                resultados[doc.id] = data
        else:
            doc = await ref.get()
            if doc.exists:
                print(f"[DOC] Documento único em {path}: {doc.to_dict()}")
                resultados = doc.to_dict()
        return resultados
    except Exception as e:
        print(f"[ERRO] Erro ao buscar subcoleção '{path}': {e}")
        return {}

# [OK] Buscar tarefas do usuário
async def buscar_tarefas_do_usuario(user_id: str):
    try:
        path = f"Clientes/{user_id}/Tarefas"
        tarefas = await buscar_subcolecao(path)
        print(f"[LIST] Tarefas encontradas: {tarefas}")
        return tarefas
    except Exception as e:
        print(f"[ERRO] Erro ao buscar tarefas do usuário {user_id}: {e}")
        return {}

# [OK] Buscar tarefas por descrição
async def buscar_tarefa_por_descricao(user_id: str, descricao: str):
    tarefas = await buscar_tarefas_do_usuario(user_id)
    for id_tarefa, dados in tarefas.items():
        if dados.get("descricao", "").lower() == descricao.lower():
            print(f"[OK] Tarefa encontrada: {id_tarefa} -> {dados}")
            return {id_tarefa: dados}
    print("[SEARCH] Nenhuma tarefa encontrada com essa descrição.")
    return {}

# [OK] Salvar dados em path (ex: Clientes/{id}/Eventos/{id})
# [AVISO] AGORA: merge=True por padrão (evita sumir estado)
async def salvar_dado_em_path(path: str, dados: dict):
    try:
        print(f"[SAVE] Tentando salvar dados em: {path}")
        for k, v in dados.items():
            print(f"   - {k}: {v} (tipo: {type(v)})")
        ref = get_ref_from_path(path)
        await ref.set(dados, merge=True)  # [OK] ALTERAÇÃO AQUI
        print(f"[OK] Dados salvos (merge) em: {path}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao salvar no caminho '{path}': {e}")
        return False

# [OK] Atualizar dados com merge
async def atualizar_dado_em_path(path: str, dados: dict):
    try:
        ref = get_ref_from_path(path)
        await ref.set(dados, merge=True)
        print(f"[OK] Dados atualizados (merge) em: {path}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar (merge) no caminho '{path}': {e}")
        return False

# [OK] Wrappers opcionais (nomes mais claros)
# patch = merge
async def patch_dado_em_path(path: str, dados: dict):
    return await atualizar_dado_em_path(path, dados)

# set = sobrescrever tudo (se você realmente precisar um dia)
# (mantido separado para não causar perda de estado sem querer)
async def set_dado_em_path(path: str, dados: dict):
    try:
        print(f"[SAVE] Tentando sobrescrever dados em: {path}")
        for k, v in dados.items():
            print(f"   - {k}: {v} (tipo: {type(v)})")
        ref = get_ref_from_path(path)
        await ref.set(dados, merge=True)
        print(f"[OK] Dados sobrescritos (set) em: {path}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao sobrescrever (set) no caminho '{path}': {e}")
        return False

# [OK] Deletar dado por path
async def deletar_dado_em_path(path: str):
    try:
        ref = get_ref_from_path(path)
        await ref.delete()
        print(f"[DELETE] Dado deletado de: {path}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao deletar no caminho '{path}': {e}")
        return False

# [OK] Limpar coleção inteira
async def limpar_colecao(colecao: str):
    try:
        docs = client.collection(colecao).stream()
        async for doc in docs:
            await client.collection(colecao).document(doc.id).delete()
        print(f"[OK] Todos os documentos da coleção '{colecao}' foram removidos!")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao limpar a coleção '{colecao}': {e}")
        return False

# [OK] Buscar todos os documentos de uma coleção (assíncrono)
async def buscar_dados(colecao: str):
    try:
        docs = client.collection(colecao).stream()
        resultados = [doc.to_dict() async for doc in docs]
        return resultados
    except Exception as e:
        print(f"[ERRO] Erro ao buscar dados da coleção '{colecao}': {e}")
        return []

# [OK] Salvar dados do cliente (com merge)
async def salvar_cliente(user_id: str, dados: dict):
    try:
        ref = client.collection("Clientes").document(user_id)
        await ref.set(dados, merge=True)
        print(f"[OK] Cliente {user_id} salvo com sucesso.")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao salvar cliente: {e}")
        return False

# [OK] Salvar dados em uma coleção (gera ID automático)
async def salvar_dados(colecao: str, dados: dict):
    try:
        await client.collection(colecao).add(dados)
        print(f"[OK] Documento salvo em '{colecao}' com dados: {dados}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao salvar dados na coleção '{colecao}': {e}")
        return False

# [OK] Buscar dado em path (documento)
async def buscar_dado_em_path(path: str):
    try:
        ref = get_ref_from_path(path)
        doc = await ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"[ERRO] Erro ao buscar dado em '{path}': {e}")
        return None

# [OK] Buscar todos os clientes (assíncrono)
async def buscar_todos_clientes():
    try:
        docs = client.collection("Clientes").stream()
        resultados = {doc.id: doc.to_dict() async for doc in docs}
        return resultados
    except Exception as e:
        print(f"[ERRO] Erro ao buscar todos os clientes: {e}")
        return {}

# [OK] Salvar evento em coleção global (opcional)
async def salvar_evento(evento_data):
    try:
        await client.collection("Eventos").add(evento_data)
        print("[OK] Evento salvo na coleção global.")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao salvar evento global: {e}")
        return False

# [OK] PATCH P2: Atualizar com operações atômicas do Firestore
async def atualizar_com_operacoes_atomicas(path: str, dados: dict):
    """
    Atualiza documento com operações atômicas do Firestore.

    Suporta:
    - firestore.Increment(n) para contadores
    - firestore.ArrayUnion([items]) para arrays
    - Valores normais para campos simples

    Usa update() ao invés de set(merge=True) para garantir atomicidade.

    Args:
        path: Path até o documento (ex: Clientes/{id}/ClienteProfiles/{cliente_id})
        dados: Dict com dados e operações atômicas

    Returns:
        True se sucesso, False se erro
    """
    try:
        from google.cloud import firestore
        ref = get_ref_from_path(path)
        await ref.update(dados)
        print(f"[OK] Dados atualizados (operações atômicas) em: {path}")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar (operações atômicas) no caminho '{path}': {e}")
        return False

# [OK] Alias para buscar documento único (para compatibilidade com /start)
async def buscar_documento(path: str):
    return await buscar_dado_em_path(path)

# [OK] Retorna o ID do dono, mesmo se for um cliente
async def obter_id_dono(user_id: str) -> str:
    cliente = await buscar_cliente(user_id)
    return cliente.get("id_negocio", user_id) if cliente else user_id

# [OK] Buscar contatos por nome (ex: Clientes/{user_id}/Contatos)
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

        print(f"[SEARCH] Contatos encontrados para '{nome}': {contatos_filtrados}")
        return contatos_filtrados
    except Exception as e:
        print(f"[ERRO] Erro ao buscar contatos: {e}")
        return []

# [OK] Buscar ID de cliente pelo nome (dentro de um negócio)
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
