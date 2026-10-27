"""
E2E TEST: Reproduz erro real onde GPT retorna dados incompletos

Simula exatamente o que vimos nos logs:
- GPT retorna JSON SEM "servico"
- Fallback falha silenciosamente
- Evento não é criado
- Erro: "Falha ao detectar profissional"

Objetivo: Validar se teste E2E captura o erro real que a vida real mostra
"""

import pytest
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
)

TENANT = "7394370553"
USER = "5511991382080"
ENDPOINT = "1350170954840548"
ACTOR_ID = f"whatsapp:{USER}"


def _webhook_payload(mensagem: str) -> dict:
    """Payload WhatsApp real"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": ENDPOINT},
                    "contacts": [{"profile": {"name": "Teste"}, "wa_id": USER}],
                    "messages": [{
                        "from": USER,
                        "id": f"wamid.real_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": mensagem},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }


@pytest.mark.asyncio
async def test_e2e_gpt_retorna_incompleto():
    """
    E2E: GPT retorna JSON INCOMPLETO (SEM servico)

    Reproduz exatamente o erro nos logs:
    📦 Conteúdo recebido da IA:
    {
      "resposta": "Bruna está disponível...",
      "acao": "criar_evento",
      "dados": {
        "data_hora": "2026-10-27T10:00:00",
        "profissional": "Bruna"
        ❌ FALTA "servico"
      }
    }
    """
    print("\n[E2E] Testando GPT retornando dados INCOMPLETOS (erro real)")

    client = app.test_client()

    # Setup: Contexto com draft completo no Firebase
    await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
        "estado_fluxo": "consultando",
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "coloracao",
            "data_hora": "2026-10-27T10:00:00"
        },
        "tenant_id": TENANT,
        "actor_id": ACTOR_ID,
    })

    # MOCK: GPT retorna dados INCOMPLETOS (como nos logs reais)
    gpt_response_incompleto = {
        "resposta": "Bruna está disponível para coloração amanhã às 10h. Posso confirmar o agendamento?",
        "acao": "criar_evento",
        "dados": {
            "data_hora": "2026-10-27T10:00:00",
            "descricao": "Coloração com Bruna",
            "duracao": 90,
            "profissional": "Bruna"
            # ❌ FALTA: "servico": "coloracao"
        }
    }

    async def mock_gpt_call(*args, **kwargs):
        """Mock que retorna resposta incompleta como GPT real faz"""
        return gpt_response_incompleto

    # Enviar mensagem que vai chamar GPT
    payload = _webhook_payload("a bruna esta disponivel amanha as 10?")

    print("\n[SETUP] Draft no Firebase: COMPLETO")
    print(f"  servico: coloracao")
    print(f"  profissional: Bruna")
    print(f"  data_hora: 2026-10-27T10:00:00")

    print("\n[MOCK] GPT vai retornar dados INCOMPLETOS")
    print(f"  servico: ❌ FALTA")
    print(f"  profissional: Bruna ✅")

    # Mockear chamar_gpt_com_contexto para retornar JSON incompleto
    with patch("main.validate_whatsapp_signature", return_value=True):
        with patch("router.principal_router.chamar_gpt_com_contexto", new_callable=AsyncMock) as mock_gpt:
            mock_gpt.return_value = gpt_response_incompleto

            print("\n[EXECUTANDO] Webhook com GPT mockado para dados incompletos...")
            response = client.post("/webhook/whatsapp", json=payload)

    print(f"\n[RESULTADO] Webhook HTTP status: {response.status_code}")

    # Verificar contexto após execução
    ctx_pos = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
    draft_pos = ctx_pos.get("draft_agendamento", {})

    print("\n[PÓS-EXECUÇÃO] Draft após webhook:")
    print(f"  servico: {draft_pos.get('servico')} (era: coloracao)")
    print(f"  profissional: {draft_pos.get('profissional')} (era: Bruna)")

    # ASSERTIVA: O teste deve FALHAR para mostrar que o fallback não funciona
    print("\n[DIAGNÓSTICO]")
    print("✅ Se servico='coloracao': Fallback FUNCIONOU")
    print("❌ Se servico=None/falta: Fallback FALHOU (erro real)")

    # Expectativa: Com fallback correto, deveria ter preenchido servico
    # Mas se falhar, vai estar vazio/None (reproduzindo o erro real)
    assert draft_pos.get("servico") == "coloracao", \
        f"ERRO REAL REPRODUZIDO: servico não foi preenchido (fallback falhou). Got: {draft_pos.get('servico')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
