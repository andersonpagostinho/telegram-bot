"""
F1-02: Backlog Comercial

Responsável por:
- Listar clientes por lead_status de forma DETERMINÍSTICA
- Usar APENAS dados de Clientes/{tenant_id}/Clientes/{cliente_actor_id}
- Não usar GPT, Sessões, ou MemoriaTemporaria
- Multi-tenant isolado

Fonte única: Firestore Clientes/{tenant_id}/Clientes/
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from services.firestore_client import get_db


async def listar_por_status(
    tenant_id: str,
    status: str
) -> List[Dict[str, Any]]:
    """
    Lista todos os clientes com um status específico.

    Args:
        tenant_id: ID do tenant (dono)
        status: um dos ESTADOS_VALIDOS

    Returns:
        Lista de documentos de clientes ordenados por ultima_interacao DESC
    """
    if not tenant_id or not status:
        return []

    try:
        db = get_db()

        # Query sem order_by para evitar índice composto
        docs = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).where("lead_status", "==", status).stream()

        clientes = []
        for doc in docs:
            cliente_dict = doc.to_dict()
            cliente_dict["actor_id"] = doc.id
            clientes.append(cliente_dict)

        # Ordenar em memória por ultima_interacao DESC
        clientes.sort(
            key=lambda x: x.get("ultima_interacao", ""),
            reverse=True
        )

        return clientes

    except Exception as e:
        print(f"[ERRO] listar_por_status: {str(e)}")
        return []


async def listar_interessados_sem_agendamento(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Lista clientes em status "interessado" que nunca agendaram.

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de clientes interessados sem agendamentos
    """
    if not tenant_id:
        return []

    try:
        db = get_db()

        # Query com dois where mas sem order_by para evitar índice composto
        docs = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).where("lead_status", "==", "interessado").where(
            "total_agendamentos", "==", 0
        ).stream()

        clientes = []
        for doc in docs:
            cliente_dict = doc.to_dict()
            cliente_dict["actor_id"] = doc.id
            clientes.append(cliente_dict)

        # Ordenar em memória por ultima_interacao DESC
        clientes.sort(
            key=lambda x: x.get("ultima_interacao", ""),
            reverse=True
        )

        return clientes

    except Exception as e:
        print(f"[ERRO] listar_interessados_sem_agendamento: {str(e)}")
        return []


async def listar_clientes_em_negociacao(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Lista clientes em status "negociacao".

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de clientes em negociação
    """
    if not tenant_id:
        return []

    return await listar_por_status(tenant_id, "negociacao")


async def listar_retorno_pendente(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Lista clientes em status "retorno_pendente".

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de clientes com retorno pendente
    """
    if not tenant_id:
        return []

    return await listar_por_status(tenant_id, "retorno_pendente")


async def listar_clientes_inativos(
    tenant_id: str
) -> List[Dict[str, Any]]:
    """
    Lista clientes em status "inativo".

    Args:
        tenant_id: ID do tenant

    Returns:
        Lista de clientes inativos
    """
    if not tenant_id:
        return []

    return await listar_por_status(tenant_id, "inativo")


async def gerar_resumo_comercial(
    tenant_id: str
) -> Dict[str, Any]:
    """
    Gera resumo comercial com contagem de clientes por status.

    Args:
        tenant_id: ID do tenant

    Returns:
        Dicionário com resumo consolidado
    """
    if not tenant_id:
        return {
            "erro": "tenant_id ausente",
            "total_clientes": 0
        }

    try:
        db = get_db()

        # Contar cada status
        estados_validos = [
            "novo",
            "interessado",
            "negociacao",
            "agendado",
            "atendido",
            "retorno_pendente",
            "inativo"
        ]

        resumo = {
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "total_clientes": 0
        }

        for estado in estados_validos:
            try:
                docs = db.collection("Clientes").document(tenant_id).collection(
                    "Clientes"
                ).where("lead_status", "==", estado).stream()

                count = sum(1 for _ in docs)
                resumo[f"total_{estado}"] = count
                resumo["total_clientes"] += count

            except Exception as e:
                print(f"[AVISO] Erro ao contar {estado}: {str(e)}")
                resumo[f"total_{estado}"] = 0

        return resumo

    except Exception as e:
        print(f"[ERRO] gerar_resumo_comercial: {str(e)}")
        return {
            "erro": str(e),
            "total_clientes": 0
        }


def formatar_resumo_para_mensagem(resumo: Dict[str, Any]) -> str:
    """
    Formata resumo comercial em mensagem legível para o dono.

    Args:
        resumo: Dicionário retornado por gerar_resumo_comercial

    Returns:
        String formatada para enviar ao dono
    """
    if resumo.get("erro"):
        return f"❌ Erro ao gerar resumo: {resumo.get('erro')}"

    total = resumo.get("total_clientes", 0)
    if total == 0:
        return "📊 Você ainda não tem nenhum cliente."

    novo = resumo.get("total_novo", 0)
    interessado = resumo.get("total_interessado", 0)
    negociacao = resumo.get("total_negociacao", 0)
    agendado = resumo.get("total_agendado", 0)
    atendido = resumo.get("total_atendido", 0)
    retorno = resumo.get("total_retorno_pendente", 0)
    inativo = resumo.get("total_inativo", 0)

    mensagem = (
        f"📊 *Resumo Comercial*\n\n"
        f"Total de clientes: *{total}*\n\n"
        f"🟢 Novo: {novo}\n"
        f"🔵 Interessado: {interessado}\n"
        f"🟡 Negociação: {negociacao}\n"
        f"🟠 Agendado: {agendado}\n"
        f"🟣 Atendido: {atendido}\n"
        f"🔴 Retorno pendente: {retorno}\n"
        f"⚫ Inativo: {inativo}"
    )

    return mensagem


def formatar_lista_para_mensagem(
    clientes: List[Dict[str, Any]],
    status: str
) -> str:
    """
    Formata lista de clientes em mensagem legível.

    Args:
        clientes: Lista de clientes
        status: Nome do status para exibição

    Returns:
        String formatada
    """
    if not clientes:
        return f"📭 Nenhum cliente em status '{status}'."

    mensagem = f"📋 *Clientes em {status}* ({len(clientes)})\n\n"

    for i, cliente in enumerate(clientes[:10], 1):  # Limitar a 10 para não poluir
        actor_id = cliente.get("actor_id", "?")
        nome = cliente.get("nome_detectado", "Sem nome")
        ultima_interacao = cliente.get("ultima_interacao", "?")

        mensagem += f"{i}. *{nome}* ({actor_id})\n"
        mensagem += f"   Última interação: {ultima_interacao}\n"

    if len(clientes) > 10:
        mensagem += f"\n... e mais {len(clientes) - 10} clientes"

    return mensagem
