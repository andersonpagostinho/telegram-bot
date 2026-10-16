"""
Gerenciamento persistente de estado de mensagens WhatsApp.

Responsabilidades:
- Marcar mensagens em PROCESSANDO (atômico via create())
- Atualizar para CONCLUIDA/FALHA_PERMANENTE/FALHA_RECUPERAVEL/ENVIO_DESCONHECIDO
- Query mensagens expiradas por endpoint (sem varredura global)
- Proteger contra atualizações por instância antiga (via instancia_id)

NÃO faz:
- Enviar mensagens (whatsapp_service.py)
- Roteamento (principal_router.py)
- Resolução de tenant (whatsapp_endpoint_service.py)

Invariante:
- Firestore = Fonte de Verdade (persiste entre restarts)
- Memória = Cache Local (perdida no restart, OK)
- Estados: PROCESSANDO → (CONCLUIDA | FALHA_PERMANENTE | FALHA_RECUPERAVEL | ENVIO_DESCONHECIDO)
- ENVIO_DESCONHECIDO: SEM retry automático (autorização obrigatória)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import uuid5, NAMESPACE_DNS

from services.firebase_service_async import get_async_client

logger = logging.getLogger(__name__)


# Exceção customizada para documento já existe (simula Firestore AlreadyExists)
class AlreadyExists(Exception):
    """Levantada quando tentamos criar um documento que já existe."""
    pass


# ==============================================================================
# AQUISIÇÃO ATÔMICA
# ==============================================================================

async def marcar_processando(
    phone_number_id: str,
    msg_id: str,
    timestamp_webhook: float
) -> bool:
    """
    Tenta marcar mensagem como PROCESSANDO atomicamente.

    Args:
        phone_number_id: ID do endpoint WhatsApp
        msg_id: ID da mensagem (de Meta)
        timestamp_webhook: Timestamp do webhook (Unix)

    Returns:
        True se conseguiu marcar (ganhou a disputa)
        False se já estava sendo processada (AlreadyExists)

    Raises:
        Exception: Erros que não sejam AlreadyExists (quota, connectivity)
    """
    try:
        # Gerar instancia_id determinístico (mesmo durante restart)
        instancia_id = str(uuid5(NAMESPACE_DNS, f"{phone_number_id}:{msg_id}:{timestamp_webhook}"))

        # Path: WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}
        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
            .document(msg_id)
        )

        # Criar atomicamente (falha se já existe)
        await ref.create({
            "status": "PROCESSANDO",
            "instancia_id": instancia_id,
            "timestamp_criacao": datetime.now(timezone.utc).isoformat(),
            "timestamp_webhook": timestamp_webhook,
            "lease_expires": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "message_id": None,  # Será preenchido se envio suceder
            "retry_count": 0,
        })

        logger.info(f"[WA-DEDUP] Mensagem marcada PROCESSANDO: {phone_number_id}/{msg_id}")
        return True

    except AlreadyExists:
        logger.info(f"[WA-DEDUP] Outra instância processando: {phone_number_id}/{msg_id}")
        return False

    except Exception as e:
        logger.error(f"[WA-DEDUP] Erro ao marcar PROCESSANDO: {e}")
        raise


# ==============================================================================
# ATUALIZAR ESTADO
# ==============================================================================

async def consultar_status(
    phone_number_id: str,
    msg_id: str
) -> Optional[str]:
    """
    Consulta status atual de uma mensagem.

    Returns:
        Status (PROCESSANDO, CONCLUIDA, ...) ou None se não encontrado
    """
    try:
        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
            .document(msg_id)
        )

        doc = await ref.get()
        if doc.exists:
            return doc.get("status")
        return None

    except Exception as e:
        logger.error(f"[WA-DEDUP] Erro ao consultar status: {e}")
        return None


async def _atualizar_status(
    phone_number_id: str,
    msg_id: str,
    novo_status: str,
    dados_adicionais: Optional[Dict[str, Any]] = None,
    timestamp_webhook: Optional[float] = None
) -> bool:
    """
    Atualiza status de uma mensagem, protegendo contra sobrescrita por instância antiga.

    Args:
        phone_number_id: ID do endpoint
        msg_id: ID da mensagem
        novo_status: CONCLUIDA, FALHA_PERMANENTE, FALHA_RECUPERAVEL, ENVIO_DESCONHECIDO
        dados_adicionais: Campos opcionais a atualizar (message_id, erro, etc)
        timestamp_webhook: Timestamp do webhook para validar instancia_id (se fornecido)

    Returns:
        True se sucesso, False se falha

    Invariante:
        - Se resultado é CONCLUIDA: nunca volta para PROCESSANDO
        - Se resultado é ENVIO_DESCONHECIDO: cleanup não sobrescreve com RECUPERAVEL
        - Se instancia_id não corresponde: rejeitar update (proteção contra versão antiga)
    """
    try:
        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
            .document(msg_id)
        )

        # [1] Validar instancia_id se fornecido
        if timestamp_webhook is not None:
            doc = await ref.get()
            if doc.exists:
                doc_instancia_id = doc.get("instancia_id")
                meu_instancia_id = str(uuid5(NAMESPACE_DNS, f"{phone_number_id}:{msg_id}:{timestamp_webhook}"))

                if doc_instancia_id != meu_instancia_id:
                    logger.warning(
                        f"[WA-DEDUP] Versão antiga tentando sobrescrever: {phone_number_id}/{msg_id} "
                        f"(doc_instancia={doc_instancia_id[:8]}... vs meu={meu_instancia_id[:8]}...)"
                    )
                    return False  # Rejeitar update

        # [2] Atualizar status
        update_data = {
            "status": novo_status,
            "timestamp_atualizacao": datetime.now(timezone.utc).isoformat(),
        }

        if dados_adicionais:
            update_data.update(dados_adicionais)

        await ref.update(update_data)

        logger.info(
            f"[WA-DEDUP] Status atualizado: {phone_number_id}/{msg_id} → {novo_status}"
        )
        return True

    except Exception as e:
        logger.error(f"[WA-DEDUP] Erro ao atualizar status: {e}")
        return False


async def marcar_concluida(
    phone_number_id: str,
    msg_id: str,
    message_id_meta: str,
    timestamp_webhook: Optional[float] = None
) -> bool:
    """
    Marca mensagem como CONCLUIDA (envio aceito por Meta).

    Args:
        phone_number_id: ID do endpoint
        msg_id: ID da mensagem
        message_id_meta: ID retornado por Meta (wamid_...)
        timestamp_webhook: Timestamp do webhook (para validar instancia_id)

    Returns:
        True se sucesso
    """
    return await _atualizar_status(
        phone_number_id,
        msg_id,
        "CONCLUIDA",
        {"message_id": message_id_meta},
        timestamp_webhook=timestamp_webhook
    )


async def marcar_falha_permanente(
    phone_number_id: str,
    msg_id: str,
    erro: str = "",
    timestamp_webhook: Optional[float] = None
) -> bool:
    """
    Marca mensagem como FALHA_PERMANENTE (erro 400/403/404).

    Não retenta.

    Args:
        timestamp_webhook: Timestamp do webhook (para validar instancia_id)

    Returns:
        True se sucesso
    """
    return await _atualizar_status(
        phone_number_id,
        msg_id,
        "FALHA_PERMANENTE",
        {"erro": erro},
        timestamp_webhook=timestamp_webhook
    )


async def marcar_falha_recuperavel(
    phone_number_id: str,
    msg_id: str,
    erro: str = "",
    timestamp_webhook: Optional[float] = None
) -> bool:
    """
    Marca mensagem como FALHA_RECUPERAVEL (erro 429/500/503).

    Será retentada via job scheduler.

    Args:
        timestamp_webhook: Timestamp do webhook (para validar instancia_id)

    Returns:
        True se sucesso
    """
    return await _atualizar_status(
        phone_number_id,
        msg_id,
        "FALHA_RECUPERAVEL",
        {"erro": erro, "proxima_tentativa": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()},
        timestamp_webhook=timestamp_webhook
    )


async def marcar_envio_desconhecido(
    phone_number_id: str,
    msg_id: str,
    erro: str = "",
    timestamp_webhook: Optional[float] = None
) -> bool:
    """
    Marca mensagem como ENVIO_DESCONHECIDO (timeout ou erro indeterminado).

    ⚠️ SEM retry automático (conforme autorização WA-P0.3).
    Persistido para revisão humana ou análise posterior.

    Args:
        timestamp_webhook: Timestamp do webhook (para validar instancia_id)

    Returns:
        True se sucesso
    """
    return await _atualizar_status(
        phone_number_id,
        msg_id,
        "ENVIO_DESCONHECIDO",
        {"erro": erro, "requer_revisao_manual": True},
        timestamp_webhook=timestamp_webhook
    )


# ==============================================================================
# RECUPERAÇÃO DE EXPIRADOS (CLEANUP SCHEDULER)
# ==============================================================================

async def listar_endpoints_ativos() -> list:
    """
    Lista todos os endpoints WhatsApp ativos.

    Assume: existe coleção WhatsAppConfig/Endpoints com lista de phone_number_id ativos.
    Se não existir, retorna lista vazia (cleanup não executa).

    Returns:
        Lista de phone_number_id
    """
    try:
        config_ref = get_async_client().collection("WhatsAppConfig").document("Endpoints")
        doc = await config_ref.get()

        if doc.exists:
            endpoints = doc.get("ativos", [])
            return endpoints if isinstance(endpoints, list) else []

        # SEM FALLBACK: Varredura global viola restrição WA-P0.3
        logger.warning("[WA-CLEANUP] WhatsAppConfig/Endpoints não configurado, cleanup não executará")
        return []

    except Exception as e:
        logger.error(f"[WA-CLEANUP] Erro ao listar endpoints: {e}")
        return []


async def recuperar_expirados(phone_number_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Query de mensagens expiradas para um endpoint específico.

    Scoped por endpoint (não varredura global).
    Procura: PROCESSANDO + lease_expires < now()

    Args:
        phone_number_id: ID do endpoint

    Returns:
        Dict {msg_id: doc_data}

    ⚠️ Índice necessário:
        Coleção: WhatsAppEndpoints/{phone_number_id}/ProcessedMessages
        Índice: (status, lease_expires)
        Criado: manualmente via console Firestore
    """
    try:
        now = datetime.now(timezone.utc).isoformat()

        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
        )

        # Query scoped ao endpoint
        query = ref.where("status", "==", "PROCESSANDO").where("lease_expires", "<", now)

        docs = query.stream()
        expirados = {}

        async for doc in docs:
            expirados[doc.id] = doc.to_dict()

        logger.info(f"[WA-CLEANUP] Encontradas {len(expirados)} mensagens expiradas em {phone_number_id}")
        return expirados

    except Exception as e:
        logger.error(f"[WA-CLEANUP] Erro ao recuperar expirados: {e}")
        return {}


async def cleanup_expirados():
    """
    Cleanup scheduler: processa mensagens expiradas.

    Executado a cada 10 minutos (via /cron/ping).

    Regras:
    - Se status == ENVIO_DESCONHECIDO: não sobrescrever com RECUPERAVEL
    - Se status == PROCESSANDO expirado: tentar marcar RECUPERAVEL (retry)
    - Se está em CONCLUIDA/FALHA_PERMANENTE: ignorar
    """
    logger.info("[WA-CLEANUP] Iniciando cleanup de mensagens expiradas")

    endpoints = await listar_endpoints_ativos()
    total_processadas = 0
    total_marcadas_retry = 0

    for endpoint_id in endpoints:
        try:
            expirados = await recuperar_expirados(endpoint_id)

            for msg_id, doc_data in expirados.items():
                try:
                    # Verificar: não sobrescrever ENVIO_DESCONHECIDO
                    if doc_data.get("message_id") == "unknown" or doc_data.get("requer_revisao_manual"):
                        # Estender lease em mais 1 hora (não marcar recuperável)
                        logger.warning(
                            f"[WA-CLEANUP] Preservando {endpoint_id}/{msg_id} "
                            f"(ENVIO_DESCONHECIDO, requer revisão)"
                        )

                        # Atualizar lease sem mudar status
                        ref = (
                            get_async_client()
                            .collection("WhatsAppEndpoints")
                            .document(endpoint_id)
                            .collection("ProcessedMessages")
                            .document(msg_id)
                        )

                        await ref.update({
                            "lease_expires": (
                                datetime.now(timezone.utc) + timedelta(hours=1)
                            ).isoformat()
                        })

                        total_processadas += 1

                    else:
                        # Marcar como FALHA_RECUPERAVEL (retry automático)
                        success = await marcar_falha_recuperavel(
                            endpoint_id,
                            msg_id,
                            "Lease expirou no PROCESSANDO"
                        )

                        if success:
                            total_marcadas_retry += 1
                            total_processadas += 1

                except Exception as e:
                    logger.error(f"[WA-CLEANUP] Erro ao processar {endpoint_id}/{msg_id}: {e}")
                    total_processadas += 1

        except Exception as e:
            logger.error(f"[WA-CLEANUP] Erro ao processar endpoint {endpoint_id}: {e}")

    logger.info(
        f"[WA-CLEANUP] Cleanup concluído: "
        f"{total_processadas} mensagens processadas, "
        f"{total_marcadas_retry} marcadas para retry"
    )
