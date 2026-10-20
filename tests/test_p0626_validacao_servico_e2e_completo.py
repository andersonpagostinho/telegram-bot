"""
[P0626] Teste E2E Completo — Validação Serviço com Firebase Real

Reproduz cenário REAL:
1. Cliente envia "voce tem agenda para corte feminino amanha as 10?"
2. Webhook processa via Flask (real, não mock)
3. Firebase é consultado (real, não mock)
4. Valida estado final + mensagem ao usuário
"""

import pytest
import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import carregar_contexto_temporario_v2, atualizar_dado_em_path

# ✅ Cliente REAL com histórico em Firestore
TENANT = "7394370553"
USER_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{USER_ID}"
PHONE_ID = "1350170954840548"

@pytest.mark.asyncio
async def test_p0626_e2e_firebase_real_webhook_real():
    """
    🧪 TESTE MODELO E2E COMPLETO

    Objetivo: Validar que a frase "voce tem agenda para corte feminino amanha as 10?"
    processa corretamente através do fluxo real

    Validações:
    - ✅ Webhook Flask recebe mensagem
    - ✅ Firebase carrega contexto real
    - ✅ Serviço é extraído corretamente
    - ✅ Estado final é validado
    """

    print("\n" + "="*80)
    print("🧪 TESTE E2E P0626 — Firebase Real + Webhook Real")
    print("="*80)

    # ETAPA 1: Limpar estado anterior para teste limpo
    print("\n[ETAPA 1] Preparando estado inicial...")
    await atualizar_dado_em_path(
        path=f"Clientes/{TENANT}/Sessoes/{ACTOR_ID}",
        dados={
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "servico": None,
            "servico_sugerido_consulta": None,
            "data": None,
            "horario": None,
            "profissional": None,
            "draft_agendamento": None,
            "multiplos_servicos_candidatos": None,
        }
    )
    print("✅ Estado limpo (pronto para teste)")

    # ETAPA 2: Enviar mensagem via webhook REAL Flask
    print("\n[ETAPA 2] Enviando mensagem via webhook Flask...")

    client = app.test_client()
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": PHONE_ID},
                    "contacts": [{"profile": {"name": "Anderson"}, "wa_id": USER_ID}],
                    "messages": [{
                        "from": USER_ID,
                        "id": f"wamid.test_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "voce tem agenda para corte feminino amanha as 10?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    print(f"Mensagem: 'voce tem agenda para corte feminino amanha as 10?'")
    print(f"Cliente: {USER_ID} | Tenant: {TENANT}")

    with patch("main.validate_whatsapp_signature", return_value=True):
        response = client.post("/webhook/whatsapp", json=payload)

    print(f"Status webhook: {response.status_code}")
    assert response.status_code == 200, f"Webhook falhou: {response.status_code}"
    print("✅ Webhook processado")

    # ETAPA 3: Aguardar processamento assíncrono
    print("\n[ETAPA 3] Aguardando processamento assíncrono...")
    await asyncio.sleep(2.0)  # Dar tempo para processamento

    # ETAPA 4: Carregar contexto do Firebase
    print("\n[ETAPA 4] Carregando contexto de Firebase...")
    ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    print(f"Estado: {ctx.get('estado_fluxo')}")
    print(f"Intenção: {ctx.get('intencao_conversacional')}")
    print(f"Serviço: {ctx.get('servico')}")
    print(f"Serviço sugerido: {ctx.get('servico_sugerido_consulta')}")
    print(f"Múltiplos candidatos: {ctx.get('multiplos_servicos_candidatos')}")

    # ETAPA 5: Validações
    print("\n[ETAPA 5] Validando resultado...")

    # ✅ V1: Estado deve ser "aguardando_servico" ou similar (fluxo iniciado)
    assert ctx.get('estado_fluxo') in ['aguardando_servico', 'consulta_disponibilidade', 'idle'], \
        f"Estado inesperado: {ctx.get('estado_fluxo')}"
    print("✅ V1: Estado OK")

    # ✅ V2: Serviço deve ser extraído ou sugerido
    servico = ctx.get('servico') or ctx.get('servico_sugerido_consulta')
    assert servico is not None, \
        f"Serviço não foi extraído! ctx={ctx}"
    print(f"✅ V2: Serviço extraído = '{servico}'")

    # ✅ V3: Serviço deve ser "corte feminino"
    assert servico.lower() == "corte feminino", \
        f"Serviço incorreto: esperado 'corte feminino', obtive '{servico}'"
    print(f"✅ V3: Serviço correto = 'corte feminino'")

    # ✅ V4: Não deve haver erro crítico no estado
    assert ctx.get('erro_critico') is None, \
        f"Erro crítico no contexto: {ctx.get('erro_critico')}"
    print("✅ V4: Sem erro crítico")

    print("\n" + "="*80)
    print("✅ TESTE PASSOU: P0626 processado corretamente!")
    print("="*80)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
