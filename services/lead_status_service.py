"""
F1-01: Serviço de Estado do Lead

Responsável por:
- Gerenciar transições de lead_status de forma DETERMINÍSTICA
- Não usa GPT para decidir estado
- Persiste em Firestore, não em sessão
- Multi-tenant isolado
- Registra auditoria de transições

Estados permitidos:
- novo: primeira mensagem do cliente
- interessado: consulta de preço/horário/serviço/disponibilidade
- negociacao: ajuste, troca, mudança de data/hora/profissional/serviço
- agendado: evento criado e confirmado
- atendido: evento concluído (se ponto existir)
- retorno_pendente: X dias após atendimento sem novo agendamento
- inativo: 30+ dias sem interação

Path: Clientes/{tenant_id}/Clientes/{cliente_actor_id}
Campos:
- lead_status
- lead_status_updated_at
- primeira_interacao
- ultima_interacao
- ultimo_atendimento
- total_agendamentos
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from services.firestore_client import get_db
import asyncio
import unicodedata


def normalizar_texto(texto: str) -> str:
    """Remove acentos e converte para minúsculas"""
    if not texto:
        return ""
    # Remove acentos
    nfd = unicodedata.normalize('NFD', texto)
    sem_acentos = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return sem_acentos.lower()


# Estados permitidos
ESTADOS_VALIDOS = {
    "novo",
    "interessado",
    "negociacao",
    "agendado",
    "atendido",
    "retorno_pendente",
    "inativo"
}


async def atualizar_lead_status(
    cliente_actor_id: str,
    tenant_id: str,
    novo_status: str,
    motivo: str = "",
    executor_id: Optional[str] = None
) -> bool:
    """
    Atualiza o status do lead de forma determinística.

    Args:
        cliente_actor_id: ID do cliente (ex: whatsapp:5511999999999)
        tenant_id: ID do tenant/dono
        novo_status: Um dos ESTADOS_VALIDOS
        motivo: Razão da transição (para auditoria)
        executor_id: Quem executou a transição (para auditoria)

    Returns:
        True se sucesso, False se erro
    """
    if not cliente_actor_id or not tenant_id:
        print(f"[ERRO] atualizar_lead_status: cliente_actor_id ou tenant_id ausente")
        return False

    if novo_status not in ESTADOS_VALIDOS:
        print(f"[ERRO] atualizar_lead_status: status invalido '{novo_status}'")
        return False

    try:
        db = get_db()
        path = f"Clientes/{tenant_id}/Clientes/{cliente_actor_id}"
        now = datetime.now(timezone.utc).isoformat()

        # Carregar estado anterior para auditoria
        doc = db.collection("Clientes").document(tenant_id).collection("Clientes").document(
            cliente_actor_id
        ).get()

        status_anterior = None
        if doc.exists:
            status_anterior = doc.to_dict().get("lead_status")

        # Preparar dados de atualização
        atualizacao = {
            "lead_status": novo_status,
            "lead_status_updated_at": now,
            "ultima_interacao": now
        }

        # Se é primeira vez que está ativo, registrar
        if status_anterior is None:
            atualizacao["primeira_interacao"] = now
            atualizacao["total_agendamentos"] = 0

        # Salvar atualização
        db.collection("Clientes").document(tenant_id).collection("Clientes").document(
            cliente_actor_id
        ).set(atualizacao, merge=True)

        # Registrar auditoria
        await registrar_auditoria_transicao(
            cliente_actor_id=cliente_actor_id,
            tenant_id=tenant_id,
            status_anterior=status_anterior,
            status_novo=novo_status,
            motivo=motivo,
            executor_id=executor_id
        )

        print(
            f"[MEC-F1-01] lead_status atualizado: {cliente_actor_id} | "
            f"{status_anterior or 'N/A'} -> {novo_status} | motivo: {motivo}"
        )
        return True

    except Exception as e:
        print(f"[ERRO] atualizar_lead_status: {str(e)}")
        return False


async def avaliar_transicao_deterministica(
    cliente_actor_id: str,
    tenant_id: str,
    mensagem: str,
    executor_id: Optional[str] = None
) -> Optional[str]:
    """
    Avalia se a mensagem deve mudar o lead_status usando REGRAS DETERMINÍSTICAS.

    Não usa GPT. Apenas analisa palavras-chave e estado existente.

    Args:
        cliente_actor_id: ID do cliente
        tenant_id: ID do tenant
        mensagem: Texto da mensagem
        executor_id: Quem enviou (para auditoria)

    Returns:
        Novo status se deve mudar, None se deve manter
    """
    if not mensagem or not isinstance(mensagem, str):
        return None

    mensagem_normalizada = normalizar_texto(mensagem)

    # Palavras-chave para "negociacao" — CHECK FIRST (mais específico)
    palavras_negociacao = [
        "mudar", "trocar", "ajustar", "adia", "depois",
        "outro", "desconto", "promocao", "oferta"
    ]

    for palavra in palavras_negociacao:
        if palavra in mensagem_normalizada:
            return "negociacao"

    # Palavras-chave para "interessado" — CHECK AFTER (mais genérico)
    palavras_interessado = [
        "preco", "valor", "custa", "horario", "hora", "quando",
        "disponivel", "disponibilidade", "servico", "quais servicos",
        "profissional", "quem faz", "marcar", "agendar"
    ]

    for palavra in palavras_interessado:
        if palavra in mensagem_normalizada:
            return "interessado"

    # Se nenhuma regra acionou, não mudar status
    return None


async def registrar_auditoria_transicao(
    cliente_actor_id: str,
    tenant_id: str,
    status_anterior: Optional[str],
    status_novo: str,
    motivo: str = "",
    executor_id: Optional[str] = None
) -> bool:
    """
    Registra auditoria de transição de lead_status.

    Args:
        cliente_actor_id: Cliente afetado
        tenant_id: Tenant
        status_anterior: Status antes
        status_novo: Status depois
        motivo: Razão
        executor_id: Quem executou

    Returns:
        True se sucesso
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        evento_auditoria = {
            "timestamp": now,
            "cliente_actor_id": cliente_actor_id,
            "status_anterior": status_anterior,
            "status_novo": status_novo,
            "motivo": motivo,
            "executor_id": executor_id or "sistema",
            "_tenant_id_guard": tenant_id
        }

        db.collection("Clientes").document(tenant_id).collection(
            "AuditoriaLeadStatus"
        ).document(f"{cliente_actor_id}_{now}").set(evento_auditoria)

        return True
    except Exception as e:
        print(f"[ERRO] registrar_auditoria_transicao: {str(e)}")
        return False


async def registrar_agendamento(
    cliente_actor_id: str,
    tenant_id: str
) -> bool:
    """
    Incrementa contador de agendamentos e atualiza ultima_interacao.

    Chamado quando evento é confirmado.

    Args:
        cliente_actor_id: Cliente
        tenant_id: Tenant

    Returns:
        True se sucesso
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        # Carregar documento atual
        doc = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).get()

        if not doc.exists:
            print(f"[ERRO] registrar_agendamento: cliente nao encontrado")
            return False

        dados = doc.to_dict()
        total_agendamentos = dados.get("total_agendamentos", 0) or 0

        # Atualizar
        atualizacao = {
            "total_agendamentos": total_agendamentos + 1,
            "ultima_interacao": now,
            "ultimo_agendamento_em": now
        }

        db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).set(atualizacao, merge=True)

        print(f"[MEC-F1-01] Agendamento registrado: {cliente_actor_id} (total: {total_agendamentos + 1})")
        return True

    except Exception as e:
        print(f"[ERRO] registrar_agendamento: {str(e)}")
        return False


async def registrar_atendimento(
    cliente_actor_id: str,
    tenant_id: str
) -> bool:
    """
    Marca que cliente foi atendido.

    Chamado quando evento.status = "concluido".

    Args:
        cliente_actor_id: Cliente
        tenant_id: Tenant

    Returns:
        True se sucesso
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        atualizacao = {
            "lead_status": "atendido",
            "lead_status_updated_at": now,
            "ultimo_atendimento": now,
            "ultima_interacao": now
        }

        db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).set(atualizacao, merge=True)

        # Auditoria
        await registrar_auditoria_transicao(
            cliente_actor_id=cliente_actor_id,
            tenant_id=tenant_id,
            status_anterior="agendado",
            status_novo="atendido",
            motivo="evento_concluido"
        )

        print(f"[MEC-F1-01] Atendimento registrado: {cliente_actor_id}")
        return True

    except Exception as e:
        print(f"[ERRO] registrar_atendimento: {str(e)}")
        return False


async def carregar_lead_status(
    cliente_actor_id: str,
    tenant_id: str
) -> Optional[str]:
    """
    Carrega o lead_status atual do cliente.

    Args:
        cliente_actor_id: Cliente
        tenant_id: Tenant

    Returns:
        lead_status ou None se não encontrado
    """
    try:
        db = get_db()

        doc = db.collection("Clientes").document(tenant_id).collection(
            "Clientes"
        ).document(cliente_actor_id).get()

        if not doc.exists:
            return None

        return doc.to_dict().get("lead_status")

    except Exception as e:
        print(f"[ERRO] carregar_lead_status: {str(e)}")
        return None
