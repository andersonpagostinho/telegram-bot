# services/lista_espera_service.py
"""
F8 MVP — ENCAIXE / LISTA DE ESPERA ATIVA

Core da funcionalidade:
- Criar registro quando cliente quer ser notificado
- Buscar compatíveis quando evento é cancelado
- Notificar cliente interessado
- Converter (criar evento) ou cancelar entrada
- Nunca usar obter_id_dono() como fonte principal: tenant_id é explícito
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import logging
from pytz import timezone

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
    atualizar_dado_em_path,
    deletar_dado_em_path,
)

logger = logging.getLogger(__name__)
FUSO_BR = timezone("America/Sao_Paulo")


# =========================================================
# CRIAR ENTRADA EM LISTA DE ESPERA
# =========================================================

async def criar_lista_espera(
    tenant_id: str,
    actor_id: str,
    cliente_id: str,
    cliente_nome: str,
    servico: str,
    profissional_preferido: str,
    data_desejada: str,  # YYYY-MM-DD
    hora_desejada: str,  # HH:MM
    duracao_minutos: int,
    evento_conflitante_id: str,
) -> Dict[str, Any]:
    """
    [F8-B] Criar registro em ListaEspera quando cliente aceita entrar.

    Args:
        tenant_id: ID do dono/salão (EXPLÍCITO, não via obter_id_dono)
        actor_id: Identificador único do cliente (ex: whatsapp:1234567890)
        cliente_id: ID do cliente em Clientes/{tenant_id}
        cliente_nome: Nome do cliente
        servico: Nome do serviço (ex: "corte", "escova")
        profissional_preferido: Nome da profissional
        data_desejada: Data em formato YYYY-MM-DD
        hora_desejada: Hora em formato HH:MM
        duracao_minutos: Duração em minutos
        evento_conflitante_id: ID do evento que causou o conflito

    Returns:
        {"status": "ok", "waitlist_id": str} ou {"status": "erro", "motivo": str}
    """
    try:
        waitlist_id = f"wait_{uuid.uuid4().hex[:12]}"
        agora = datetime.now(FUSO_BR)

        # Expiração: 2 dias a partir de agora
        expira_em = agora + timedelta(days=2)

        documento = {
            "waitlist_id": waitlist_id,
            "tenant_id": tenant_id,
            "cliente": {
                "actor_id": actor_id,
                "cliente_id": cliente_id,
                "cliente_nome": cliente_nome,
            },
            "servico_desejado": {
                "servico": servico,
                "profissional_preferido": profissional_preferido,
                "data_desejada": data_desejada,
                "hora_desejada": hora_desejada,
                "duracao_minutos": duracao_minutos,
            },
            "status": "ativo",
            "origem_evento_conflitante_id": evento_conflitante_id,
            "auditoria": {
                "criado_em": agora.isoformat(),
                "expira_em": expira_em.isoformat(),
                "ultima_notificacao_em": None,
                "tentativas_notificacao": 0,
                "confirmado_em": None,
            },
            "notificacao": {
                "canal": "whatsapp",
                "enviada": False,
            },
            "confirmacao_pendente": False,
        }

        path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"
        await salvar_dado_em_path(path, documento)

        logger.info(
            f"[WAITLIST_CRIADA] waitlist_id={waitlist_id} | "
            f"cliente={cliente_id} | servico={servico} | prof={profissional_preferido}"
        )

        return {"status": "ok", "waitlist_id": waitlist_id}

    except Exception as e:
        logger.error(f"❌ criar_lista_espera: {e}", exc_info=True)
        return {"status": "erro", "motivo": str(e)}


# =========================================================
# BUSCAR ENTRADA COMPATÍVEL PARA NOTIFICAÇÃO
# =========================================================

async def buscar_proxima_lista_espera_compativel(
    tenant_id: str,
    servico: str,
    profissional_preferido: str,
    data_desejada: str,  # YYYY-MM-DD
    hora_desejada: str,  # HH:MM
    duracao_minutos: int,
) -> Optional[Dict[str, Any]]:
    """
    [F8-C] Buscar primeira entrada em ListaEspera que seja compatível com vaga aberta.

    Critérios:
    - status = "ativo"
    - servico_desejado.servico = servico
    - servico_desejado.profissional_preferido = profissional_preferido
    - servico_desejado.data_desejada = data_desejada
    - servico_desejado.hora_desejada = hora_desejada
    - servico_desejado.duracao_minutos <= duracao_minutos (permite mais tempo, não menos)
    - Ordenar por criado_em ASC (FIFO)

    Returns:
        Primeiro documento encontrado ou None
    """
    try:
        lista_espera = await buscar_subcolecao(f"Clientes/{tenant_id}/ListaEspera") or {}

        candidatos = []

        for waitlist_id, doc in lista_espera.items():
            if not isinstance(doc, dict):
                continue

            # Filtrar por status
            if doc.get("status") != "ativo":
                continue

            # Filtrar por compatibilidade
            servico_des = doc.get("servico_desejado") or {}

            if (
                servico_des.get("servico") != servico
                or servico_des.get("profissional_preferido") != profissional_preferido
                or servico_des.get("data_desejada") != data_desejada
                or servico_des.get("hora_desejada") != hora_desejada
            ):
                continue

            # Duração: waitlist pode ter duração <= disponível (flexibilidade)
            duracao_waitlist = servico_des.get("duracao_minutos", 0)
            if duracao_waitlist > duracao_minutos:
                logger.warning(
                    f"[WAITLIST_REJEITADA] waitlist requer {duracao_waitlist}min "
                    f"mas vaga tem {duracao_minutos}min"
                )
                continue

            # Adicionar à lista de candidatos
            auditoria = doc.get("auditoria") or {}
            criado_em_str = auditoria.get("criado_em", "")
            candidatos.append((criado_em_str, waitlist_id, doc))

        if not candidatos:
            return None

        # Ordenar por criado_em (FIFO) e retornar primeiro
        candidatos.sort(key=lambda x: x[0])
        _, _, doc = candidatos[0]

        logger.info(
            f"[WAITLIST_ENCONTRADA] servico={servico} | prof={profissional_preferido} | "
            f"data={data_desejada} {hora_desejada}"
        )

        return doc

    except Exception as e:
        logger.error(f"❌ buscar_proxima_lista_espera_compativel: {e}", exc_info=True)
        return None


# =========================================================
# MARCAR COMO NOTIFICADO
# =========================================================

async def marcar_como_notificado(
    tenant_id: str,
    waitlist_id: str,
) -> bool:
    """
    [F8-D] Marcar entrada como "notificado" após enviar mensagem ao cliente.

    Atualiza:
    - status: "ativo" → "notificado"
    - ultima_notificacao_em: agora
    - tentativas_notificacao: +1
    - notificacao.enviada: True

    Returns:
        True se sucesso, False se erro
    """
    try:
        path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"

        agora = datetime.now(FUSO_BR)

        # Buscar doc atual para incrementar tentativas
        doc = await buscar_dado_em_path(path) or {}
        tentativas = (doc.get("auditoria") or {}).get("tentativas_notificacao") or 0

        payload = {
            "status": "notificado",
            "auditoria": {
                "ultima_notificacao_em": agora.isoformat(),
                "tentativas_notificacao": tentativas + 1,
            },
            "notificacao": {
                "enviada": True,
            },
            "confirmacao_pendente": True,
        }

        await atualizar_dado_em_path(path, payload)

        logger.info(
            f"[WAITLIST_NOTIFICADA] waitlist_id={waitlist_id} | "
            f"tentativa={tentativas + 1}"
        )

        return True

    except Exception as e:
        logger.error(f"❌ marcar_como_notificado: {e}", exc_info=True)
        return False


# =========================================================
# MARCAR COMO CONVERTIDO (EVENTO CRIADO)
# =========================================================

async def marcar_como_convertido(
    tenant_id: str,
    waitlist_id: str,
    evento_id: str,
) -> bool:
    """
    [F8-G] Marcar entrada como "convertido" após evento ser criado com sucesso.

    Atualiza:
    - status: "notificado" → "convertido"
    - confirmado_em: agora
    - evento_criado_apos_encaixe: evento_id

    Returns:
        True se sucesso, False se erro
    """
    try:
        path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"

        agora = datetime.now(FUSO_BR)

        payload = {
            "status": "convertido",
            "auditoria": {
                "confirmado_em": agora.isoformat(),
            },
            "evento_criado_apos_encaixe": evento_id,
            "confirmacao_pendente": False,
        }

        await atualizar_dado_em_path(path, payload)

        logger.info(
            f"[WAITLIST_CONVERTIDA] waitlist_id={waitlist_id} | evento_id={evento_id}"
        )

        return True

    except Exception as e:
        logger.error(f"❌ marcar_como_convertido: {e}", exc_info=True)
        return False


# =========================================================
# MARCAR COMO CANCELADO
# =========================================================

async def marcar_como_cancelado(
    tenant_id: str,
    waitlist_id: str,
) -> bool:
    """
    [F8-D/E] Marcar entrada como "cancelado" quando cliente recusa ou fluxo não completa.

    Atualiza:
    - status: "notificado"/"ativo" → "cancelado"
    - confirmacao_pendente: False

    Returns:
        True se sucesso, False se erro
    """
    try:
        path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"

        payload = {
            "status": "cancelado",
            "confirmacao_pendente": False,
        }

        await atualizar_dado_em_path(path, payload)

        logger.info(f"[WAITLIST_CANCELADA] waitlist_id={waitlist_id}")

        return True

    except Exception as e:
        logger.error(f"❌ marcar_como_cancelado: {e}", exc_info=True)
        return False


# =========================================================
# BUSCAR POR WAITLIST_ID (para validação)
# =========================================================

async def buscar_lista_espera_por_id(
    tenant_id: str,
    waitlist_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Buscar documento específico de ListaEspera.

    Returns:
        Documento ou None se não encontrado
    """
    try:
        path = f"Clientes/{tenant_id}/ListaEspera/{waitlist_id}"
        doc = await buscar_dado_em_path(path)
        return doc if isinstance(doc, dict) else None
    except Exception as e:
        logger.error(f"❌ buscar_lista_espera_por_id: {e}", exc_info=True)
        return None
