# services/whatsapp_service.py
"""
Serviço real de envio de mensagens via Meta WhatsApp Cloud API.

Responsabilidades:
- Envio de mensagens para wa_id via phone_number_id
- Integração com Meta Graph API
- Tratamento seguro de credenciais
- Logging de sucesso/erro sem expor secrets

NÃO faz:
- Resolução de tenant (feito pelo caller)
- Validação de negócio (feito pelo caller)
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Configuração de Meta Graph API
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")
META_GRAPH_API_BASE_URL = os.getenv("META_GRAPH_API_BASE_URL", "https://graph.instagram.com")


async def enviar_mensagem_whatsapp(
    destinatario_id: str,
    mensagem: str,
    phone_number_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envia mensagem via Meta WhatsApp Cloud API.

    Se phone_number_id for None, tenta usar META_PHONE_NUMBER_ID do ambiente.

    Args:
        destinatario_id: wa_id do destinatário (ex: 5519990068427)
        mensagem: Texto da mensagem
        phone_number_id: ID do endpoint WhatsApp (opcional se em .env)

    Returns:
        Dict com:
        {
            "success": True/False,
            "message_id": "wamid.XX..." (se sucesso),
            "status_code": 200/400/etc,
            "error": "Descrição do erro" (se falha)
        }
    """
    # Obter credenciais do ambiente
    access_token = os.getenv("META_ACCESS_TOKEN")
    if not phone_number_id:
        phone_number_id = os.getenv("META_PHONE_NUMBER_ID")

    if not access_token:
        logger.error("[WA] META_ACCESS_TOKEN não configurado")
        return {
            "success": False,
            "status_code": 500,
            "error": "Credencial de acesso não configurada"
        }

    if not phone_number_id:
        logger.error("[WA] phone_number_id não fornecido e META_PHONE_NUMBER_ID não configurado")
        return {
            "success": False,
            "status_code": 500,
            "error": "Endpoint WhatsApp não configurado"
        }

    if not destinatario_id or not mensagem:
        logger.error(f"[WA] Parâmetros inválidos: destinatario_id={bool(destinatario_id)} mensagem={bool(mensagem)}")
        return {
            "success": False,
            "status_code": 400,
            "error": "Destinatário ou mensagem vazio"
        }

    # Construir payload conforme Meta WhatsApp Cloud API
    url = f"{META_GRAPH_API_BASE_URL}/{META_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": destinatario_id,
        "type": "text",
        "text": {
            "body": mensagem
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        # Sucesso (Meta retorna 200 ou 201 com message_id)
        if response.status_code in [200, 201]:
            data = response.json()
            messages = data.get("messages", [])
            if messages and isinstance(messages, list):
                message_id = messages[0].get("id")
                logger.info(f"[WA] Mensagem enviada: message_id={message_id} to={destinatario_id}")
                return {
                    "success": True,
                    "message_id": message_id,
                    "status_code": response.status_code
                }
            else:
                logger.warning(f"[WA] Resposta sucesso sem message_id: {data}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message_id": "unknown"
                }

        # Erro HTTP
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            except Exception:
                error_msg = f"HTTP {response.status_code}"

            logger.error(f"[WA] Falha ao enviar: status={response.status_code} to={destinatario_id} error={error_msg}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_msg
            }

    except httpx.TimeoutException:
        logger.error(f"[WA] Timeout ao enviar para {destinatario_id}")
        return {
            "success": False,
            "status_code": 504,
            "error": "Timeout ao contatar Meta API"
        }

    except Exception as e:
        logger.error(f"[WA] Exceção ao enviar para {destinatario_id}: {e}")
        return {
            "success": False,
            "status_code": 500,
            "error": str(e)
        }
