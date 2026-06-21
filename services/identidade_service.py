# Serviço de Identidade por Canal
# Responsabilidade: Resolver e gerenciar identidades (dono, profissional, cliente)
# Canal → actor_id → tenant_id → tipo_usuario → permissões

import asyncio
from datetime import datetime
import pytz
from services.firestore_client import get_db

# Normalização de canal e identificador
CANAIS_VALIDOS = ["whatsapp", "sms", "voz", "email", "web"]


def normalizar_actor_id(canal: str, identificador: str) -> str:
    """
    Normaliza canal + identificador para actor_id.

    Formato: canal:identificador
    Exemplo: whatsapp:11999999999, email:usuario@email.com

    Args:
        canal: "whatsapp", "sms", "voz", "email", "web"
        identificador: número, email, ou ID único

    Returns:
        actor_id normalizado
    """
    if not canal or not identificador:
        raise ValueError("Canal e identificador são obrigatórios")

    canal = canal.lower().strip()
    identificador = identificador.strip()

    if canal not in CANAIS_VALIDOS:
        raise ValueError(f"Canal inválido: {canal}. Válidos: {CANAIS_VALIDOS}")

    # Remove caracteres especiais de telefone/email
    if canal in ["whatsapp", "sms"]:
        identificador = ''.join(c for c in identificador if c.isdigit())
    elif canal == "email":
        identificador = identificador.lower()

    actor_id = f"{canal}:{identificador}"
    return actor_id


async def resolver_ator_por_canal(tenant_id: str, canal: str, identificador: str) -> dict | None:
    """
    Resolve um ator existente pelo canal e identificador.

    Path: Clientes/{tenant_id}/Atores/{actor_id}

    Args:
        tenant_id: ID do tenant (dono)
        canal: tipo de canal
        identificador: valor do canal

    Returns:
        Documento do ator ou None se não encontrado
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório")

    try:
        actor_id = normalizar_actor_id(canal, identificador)

        doc = await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Atores").document(actor_id).get()
        )

        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"[ERRO] Resolver ator: {e}")
        return None


async def criar_ator_dono(tenant_id: str, canal: str, identificador: str, nome: str, email: str) -> dict:
    """
    Cria um novo ator DONO (administrador do tenant).

    Path: Clientes/{tenant_id}/Atores/{actor_id}

    Args:
        tenant_id: ID do tenant (pode ser novo)
        canal: tipo de canal (whatsapp, sms, email, etc)
        identificador: valor único do canal
        nome: nome do dono
        email: email do dono

    Returns:
        Documento criado do ator dono
    """
    if not tenant_id or not canal or not identificador or not nome:
        raise ValueError("tenant_id, canal, identificador e nome são obrigatórios")

    try:
        actor_id = normalizar_actor_id(canal, identificador)
        now = datetime.now(pytz.UTC).isoformat()

        ator_data = {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "canal": canal,
            "identificador": identificador,
            "tipo_usuario": "dono",
            "nome": nome,
            "email": email,
            "ativo": True,
            "criado_em": now,
            "criado_por": "sistema",
            "atualizado_em": now,
            "permissoes": ["admin", "ler", "escrever", "deletar"]
        }

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Atores").document(actor_id).set(ator_data)
        )

        print(f"[OK] Ator DONO criado: {actor_id} (tenant: {tenant_id})")
        return ator_data
    except Exception as e:
        print(f"[ERRO] Criar ator dono: {e}")
        raise


async def criar_ator_cliente_automatico(tenant_id: str, canal: str, identificador: str, nome_detectado: str = "") -> dict:
    """
    Cria um novo ator CLIENTE automaticamente no primeiro contato.

    Path: Clientes/{tenant_id}/Atores/{actor_id}

    Args:
        tenant_id: ID do tenant
        canal: tipo de canal
        identificador: valor do canal
        nome_detectado: nome extraído da conversa (opcional)

    Returns:
        Documento criado do ator cliente
    """
    if not tenant_id or not canal or not identificador:
        raise ValueError("tenant_id, canal e identificador são obrigatórios")

    try:
        actor_id = normalizar_actor_id(canal, identificador)
        now = datetime.now(pytz.UTC).isoformat()

        ator_data = {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "canal": canal,
            "identificador": identificador,
            "tipo_usuario": "cliente",
            "nome": nome_detectado or "",
            "ativo": True,
            "criado_em": now,
            "criado_por": "primeiro_contato",
            "atualizado_em": now,
            "permissoes": ["ler", "agendamento"]
        }

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Atores").document(actor_id).set(ator_data)
        )

        # Registrar também na coleção Clientes para histórico
        cliente_data = {
            "actor_id": actor_id,
            "nome_detectado": nome_detectado or "",
            "canal": canal,
            "identificador": identificador,
            "origem": "primeiro_contato",
            "criado_em": now,
            "criado_por": "sistema_autodeteccao",
            "ativo": True,
            "tenant_id": tenant_id,
            "primeiro_contato_em": now,
            "ultimo_contato_em": now
        }

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Clientes").document(actor_id).set(cliente_data)
        )

        print(f"[OK] Ator CLIENTE criado automaticamente: {actor_id} (tenant: {tenant_id})")
        return ator_data
    except Exception as e:
        print(f"[ERRO] Criar ator cliente automático: {e}")
        raise


async def criar_ator_profissional(tenant_id: str, canal: str, identificador: str, nome: str, criado_por: str) -> dict:
    """
    Cria um novo ator PROFISSIONAL (cadastrado pelo dono).

    Path: Clientes/{tenant_id}/Atores/{actor_id}

    Args:
        tenant_id: ID do tenant
        canal: tipo de canal (whatsapp, sms, email, etc)
        identificador: valor único do canal (telefone, email, etc)
        nome: nome do profissional
        criado_por: actor_id do dono que cadastrou

    Returns:
        Documento criado do ator profissional
    """
    if not tenant_id or not canal or not identificador or not nome or not criado_por:
        raise ValueError("tenant_id, canal, identificador, nome e criado_por são obrigatórios")

    try:
        actor_id = normalizar_actor_id(canal, identificador)
        now = datetime.now(pytz.UTC).isoformat()

        ator_data = {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "canal": canal,
            "identificador": identificador,
            "tipo_usuario": "profissional",
            "nome": nome,
            "ativo": True,
            "criado_em": now,
            "criado_por": criado_por,
            "atualizado_em": now,
            "permissoes": ["ler", "operacional"]
        }

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Atores").document(actor_id).set(ator_data)
        )

        print(f"[OK] Ator PROFISSIONAL criado: {actor_id} (tenant: {tenant_id})")
        return ator_data
    except Exception as e:
        print(f"[ERRO] Criar ator profissional: {e}")
        raise


async def roteador_por_tipo_usuario(tenant_id: str, actor_id: str) -> dict | None:
    """
    Resolve um ator pelo actor_id e retorna tipo_usuario para roteamento.

    Este é o ponto de entrada para determinar permissões.

    Args:
        tenant_id: ID do tenant
        actor_id: actor_id normalizado

    Returns:
        {"tipo_usuario": "dono|profissional|cliente", "ator": {...}}
        ou None se não encontrado
    """
    if not tenant_id or not actor_id:
        return None

    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Atores").document(actor_id).get()
        )

        if not doc.exists:
            return None

        ator = doc.to_dict()
        return {
            "tipo_usuario": ator.get("tipo_usuario"),
            "ator": ator
        }
    except Exception as e:
        print(f"[ERRO] Roteador por tipo: {e}")
        return None


async def atualizar_ultimo_contato(tenant_id: str, actor_id: str) -> bool:
    """
    Atualiza o timestamp do último contato de um cliente.

    Args:
        tenant_id: ID do tenant
        actor_id: actor_id do cliente

    Returns:
        True se atualizado, False caso contrário
    """
    if not tenant_id or not actor_id:
        return False

    try:
        now = datetime.now(pytz.UTC).isoformat()

        await asyncio.to_thread(
            lambda: get_db().collection("Clientes").document(tenant_id).collection("Clientes").document(actor_id).update({
                "ultimo_contato_em": now,
                "atualizado_em": now
            })
        )
        return True
    except Exception as e:
        print(f"[AVISO] Atualizar último contato: {e}")
        return False


async def buscar_profissional_por_nome(tenant_id: str, nome: str) -> dict | None:
    """
    Busca um profissional pelo nome no tenant.

    Args:
        tenant_id: ID do tenant
        nome: nome do profissional (ou parte dele)

    Returns:
        Documento do ator profissional ou None
    """
    if not tenant_id or not nome:
        return None

    try:
        docs = await asyncio.to_thread(
            lambda: list(get_db().collection("Clientes").document(tenant_id).collection("Atores")
                    .where("tipo_usuario", "==", "profissional")
                    .where("nome", "==", nome)
                    .limit(1)
                    .stream())
        )

        if docs:
            return docs[0].to_dict()
        return None
    except Exception as e:
        print(f"[ERRO] Buscar profissional: {e}")
        return None


async def listar_profissionais(tenant_id: str) -> list:
    """
    Lista todos os profissionais ativos do tenant.

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de documentos de profissionais
    """
    if not tenant_id:
        return []

    try:
        docs = await asyncio.to_thread(
            lambda: list(get_db().collection("Clientes").document(tenant_id).collection("Atores")
                    .where("tipo_usuario", "==", "profissional")
                    .where("ativo", "==", True)
                    .stream())
        )

        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"[ERRO] Listar profissionais: {e}")
        return []
