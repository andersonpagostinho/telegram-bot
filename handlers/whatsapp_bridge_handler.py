"""
DESATIVADO TEMPORARIAMENTE

Handler para ponte WhatsApp Adapter → NeoEve Core

Motivo: bloqueio do número de testes pelo WhatsApp.

Este arquivo contém a lógica de integração com o adapter WhatsApp.
Está preservado para futuro reuso quando uma estratégia oficial
for definida (Cloud API ou outro canal aprovado).

Para reativar manualmente, execute:
  npm run whatsapp:dev

Responsabilidades (quando ativo):
1. Receber requisição POST de /whatsapp/incoming
2. Extrair actor_id, tenant_id, texto
3. Chamar principal_router para processar
4. Retornar resposta ao adapter

Não faz:
- Validação de role/contexto (fica no router)
- Cálculo de agenda (fica no router)
- Acesso direto a Firestore (fica no router)
- Decisão de lógica de negócio (fica no router)
"""

import logging
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


async def processar_mensagem_whatsapp(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processar mensagem recebida do WhatsApp.

    Entrada:
    {
      "canal": "whatsapp",
      "tenant_id": "7394370553",
      "neoeve_number": "5519994443694",
      "actor_id": "5519999999999",
      "texto": "oi"
    }

    Saída:
    {
      "canal": "whatsapp",
      "actor_id": "5519999999999",
      "tenant_id": "7394370553",
      "resposta": "<resposta_do_núcleo>"
    }
    """

    try:
        # ====================================================================
        # VALIDAR PAYLOAD
        # ====================================================================
        canal = payload.get("canal")
        tenant_id = payload.get("tenant_id")
        neoeve_number = payload.get("neoeve_number")
        actor_id = payload.get("actor_id")
        texto = payload.get("texto", "").strip()

        if not all([canal, tenant_id, actor_id, texto]):
            logger.error(
                f"[WHATSAPP_BRIDGE] Payload incompleto: "
                f"canal={canal}, tenant_id={tenant_id}, actor_id={actor_id}, texto={bool(texto)}"
            )
            return {
                "canal": "whatsapp",
                "actor_id": actor_id,
                "tenant_id": tenant_id,
                "resposta": "Desculpa, houve um erro ao processar sua mensagem.",
                "erro": "Payload incompleto",
            }

        logger.info(
            f"[WHATSAPP_BRIDGE] Mensagem recebida | "
            f"canal={canal} | tenant_id={tenant_id} | actor_id={actor_id} | texto='{texto}'"
        )

        # ====================================================================
        # CHAMAR ROUTER PRINCIPAL
        # ====================================================================
        from router.principal_router import roteador_principal

        # Chamar roteador com as informações do WhatsApp
        # O roteador vai automaticamente identificar o papel/contexto pelo actor_id
        resposta = await roteador_principal(
            user_id=actor_id,
            mensagem=texto,
            update=None,  # WhatsApp não tem update object do Telegram
            context=None,  # WhatsApp não tem context do Telegram
        )

        logger.info(
            f"[WHATSAPP_BRIDGE] Resposta gerada | "
            f"actor_id={actor_id} | resposta='{resposta}'"
        )

        return {
            "canal": "whatsapp",
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "resposta": resposta,
        }

    except Exception as e:
        logger.exception(f"[WHATSAPP_BRIDGE] Erro ao processar mensagem: {e}")
        return {
            "canal": "whatsapp",
            "actor_id": payload.get("actor_id"),
            "tenant_id": payload.get("tenant_id"),
            "resposta": "Desculpa, estou com instabilidade. Tente novamente em alguns segundos.",
            "erro": str(e),
        }


async def handle_whatsapp_incoming(request) -> Dict[str, Any]:
    """
    Endpoint FastAPI/Flask para /whatsapp/incoming

    POST /whatsapp/incoming
    Content-Type: application/json

    {
      "canal": "whatsapp",
      "tenant_id": "7394370553",
      "neoeve_number": "5519994443694",
      "actor_id": "5519999999999",
      "texto": "oi"
    }

    Response:
    {
      "canal": "whatsapp",
      "actor_id": "5519999999999",
      "tenant_id": "7394370553",
      "resposta": "<resposta>"
    }
    """
    try:
        # Extrair JSON do request (será adaptado conforme o framework usado)
        payload = await request.json()

        logger.info(f"[WHATSAPP_BRIDGE] POST recebido: {payload}")

        # Processar mensagem
        resultado = await processar_mensagem_whatsapp(payload)

        return resultado

    except Exception as e:
        logger.exception(f"[WHATSAPP_BRIDGE] Erro ao processar request: {e}")
        return {
            "erro": str(e),
            "resposta": "Desculpa, erro ao processar sua mensagem.",
        }
