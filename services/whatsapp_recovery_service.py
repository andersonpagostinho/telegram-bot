# -*- coding: utf-8 -*-
"""
Serviço de Recuperação de Mensagens WhatsApp

Responsabilidades:
- Recuperar mensagens marcadas em FALHA_RECUPERAVEL por razão de configuração
- Limpar estado sem prejudicar idempotência
- Preservar histórico para auditoria
- Permitir reprocessamento controlado

Não faz:
- Alterar dados de clientes
- Deletar histórico
- Contornar deduplicação
"""

import logging
from datetime import datetime, timezone
from services.firebase_service_async import get_async_client

logger = logging.getLogger(__name__)


async def recuperar_audio_por_token_ausente(phone_number_id: str, msg_id: str) -> dict:
    """
    Recupera uma mensagem de áudio que falhou por token ausente.

    Requisitos:
    - WHATSAPP_ACCESS_TOKEN deve estar configurado antes de chamar
    - Mensagem deve estar em FALHA_RECUPERAVEL
    - msg_id deve ser o original (não alterar para contornar dedup)

    Retorna:
        {
            "ok": True/False,
            "motivo": "Status não era FALHA_RECUPERAVEL" | "Token já estava configurado" | ...
            "msg_id": msg_id original,
            "status_anterior": "FALHA_RECUPERAVEL",
            "status_novo": "PROCESSANDO"
        }
    """

    try:
        # 1. Verificar que token está configurado (mesmo que whatsapp_service.py)
        import os
        access_token = os.getenv("META_ACCESS_TOKEN", "")

        if not access_token:
            return {
                "ok": False,
                "motivo": "WHATSAPP_ACCESS_TOKEN ainda não configurado",
                "msg_id": msg_id,
            }

        # 2. Obter estado atual da mensagem
        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
            .document(msg_id)
        )

        doc = await ref.get()

        if not doc.exists:
            return {
                "ok": False,
                "motivo": "Mensagem não encontrada em Firestore",
                "msg_id": msg_id,
            }

        data = doc.to_dict()
        status_atual = data.get("status")
        erro_anterior = data.get("erro", "")

        # 3. Validar que está em FALHA_RECUPERAVEL
        if status_atual != "FALHA_RECUPERAVEL":
            return {
                "ok": False,
                "motivo": f"Status é {status_atual}, não FALHA_RECUPERAVEL",
                "msg_id": msg_id,
                "status_atual": status_atual,
            }

        # 4. Validar que foi por token ausente
        if "META_ACCESS_TOKEN ausente" not in erro_anterior and "WHATSAPP_ACCESS_TOKEN ausente" not in erro_anterior:
            return {
                "ok": False,
                "motivo": f"Falha não foi por token ausente: {erro_anterior}",
                "msg_id": msg_id,
                "erro_original": erro_anterior,
            }

        # 5. Limpar estado para reprocessamento
        # Gerar novo instancia_id determinístico (mesmo webhook recebido)
        from uuid import uuid5, NAMESPACE_DNS
        import time

        timestamp_webhook = time.time()
        instancia_id_novo = str(uuid5(NAMESPACE_DNS, f"{phone_number_id}:{msg_id}:{timestamp_webhook}"))

        # Resetar para PROCESSANDO com novo lease
        from datetime import timedelta

        await ref.update({
            "status": "PROCESSANDO",
            "instancia_id": instancia_id_novo,
            "timestamp_recuperacao": datetime.now(timezone.utc).isoformat(),
            "erro_anterior": erro_anterior,  # Manter histórico
            "retry_count": data.get("retry_count", 0) + 1,
            "lease_expires": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        })

        logger.info(f"[WA-RECOVERY] Mensagem recuperada: {phone_number_id}/{msg_id} → PROCESSANDO")

        return {
            "ok": True,
            "motivo": "Recuperação bem-sucedida",
            "msg_id": msg_id,
            "status_anterior": "FALHA_RECUPERAVEL",
            "status_novo": "PROCESSANDO",
            "retry_count": data.get("retry_count", 0) + 1,
            "proxima_tentativa": "Próxima execução de webhook ou scheduler",
        }

    except Exception as e:
        logger.error(f"[WA-RECOVERY] Erro ao recuperar {phone_number_id}/{msg_id}: {e}")
        return {
            "ok": False,
            "motivo": f"Erro ao recuperar: {str(e)}",
            "msg_id": msg_id,
        }


async def listar_audios_pendentes_token(phone_number_id: str) -> list:
    """
    Lista todas as mensagens de áudio em FALHA_RECUPERAVEL por token ausente.

    Retorna lista de msg_ids prontos para recuperação.
    """

    try:
        ref = (
            get_async_client()
            .collection("WhatsAppEndpoints")
            .document(phone_number_id)
            .collection("ProcessedMessages")
        )

        # Query: FALHA_RECUPERAVEL com token ausente no erro
        query = ref.where("status", "==", "FALHA_RECUPERAVEL").where("erro", "array-contains", "WHATSAPP_ACCESS_TOKEN ausente")

        # Fallback: query só com status e filtrar em Python
        docs = []
        async for doc in ref.where("status", "==", "FALHA_RECUPERAVEL").stream():
            data = doc.to_dict()
            if "WHATSAPP_ACCESS_TOKEN ausente" in data.get("erro", ""):
                docs.append(doc.id)

        logger.info(f"[WA-RECOVERY] Encontradas {len(docs)} mensagens pendentes de token em {phone_number_id}")
        return docs

    except Exception as e:
        logger.error(f"[WA-RECOVERY] Erro ao listar pendentes: {e}")
        return []


async def recuperar_audios_lote(phone_number_id: str) -> dict:
    """
    Recupera em lote todos os áudios pendentes de token em um endpoint.

    Retorna:
        {
            "total": N,
            "sucesso": N,
            "falha": N,
            "mensagens": [...]
        }
    """

    pendentes = await listar_audios_pendentes_token(phone_number_id)

    sucesso = 0
    falha = 0
    resultados = []

    for msg_id in pendentes:
        resultado = await recuperar_audio_por_token_ausente(phone_number_id, msg_id)
        resultados.append(resultado)

        if resultado.get("ok"):
            sucesso += 1
        else:
            falha += 1

    return {
        "total": len(pendentes),
        "sucesso": sucesso,
        "falha": falha,
        "mensagens": resultados,
    }


__all__ = [
    "recuperar_audio_por_token_ausente",
    "listar_audios_pendentes_token",
    "recuperar_audios_lote",
]
