"""
[P0626] Teste com Serviço Diferente — MANICURE

Valida se a falha é específica para "corte feminino" ou genérica para qualquer serviço.
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

TENANT = "7394370553"
USER_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{USER_ID}"
PHONE_ID = "1350170954840548"

@pytest.mark.asyncio
async def test_manicure_servico_extraido():
    """
    Testa: "voce tem agenda para manicure amanha as 10?"
    Compara com: "voce tem agenda para corte feminino amanha as 10?"
    """

    print("\n" + "="*80)
    print("🧪 TESTE P0626 — MANICURE (vs CORTE FEMININO)")
    print("="*80)

    client = app.test_client()

    # Limpeza
    print("\n[PREP] Limpando estado...")
    await atualizar_dado_em_path(
        path=f"Clientes/{TENANT}/Sessoes/{ACTOR_ID}",
        dados={
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "servico": None,
            "servico_sugerido_consulta": None,
            "draft_agendamento": None,
        }
    )
    print("✅ Limpo")

    # MSG 1: MANICURE
    print("\n" + "-"*80)
    print("[MSG 1] Testando: 'voce tem agenda para manicure amanha as 10?'")
    print("-"*80)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": PHONE_ID},
                    "contacts": [{"profile": {"name": "Teste"}, "wa_id": USER_ID}],
                    "messages": [{
                        "from": USER_ID,
                        "id": f"manicure_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "voce tem agenda para manicure amanha as 10?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    with patch("main.validate_whatsapp_signature", return_value=True):
        response = client.post("/webhook/whatsapp", json=payload)

    print(f"[HTTP] Status: {response.status_code}")

    await asyncio.sleep(1.5)

    ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    print(f"\n[RESULTADO]")
    print(f"  estado_fluxo: {ctx.get('estado_fluxo')}")
    print(f"  intencao_conversacional: {ctx.get('intencao_conversacional')}")
    print(f"  servico: {ctx.get('servico')}")
    print(f"  servico_sugerido_consulta: {ctx.get('servico_sugerido_consulta')}")

    servico = ctx.get('servico') or ctx.get('servico_sugerido_consulta')

    print(f"\n[VALIDACAO]")
    if servico:
        print(f"✅ MANICURE EXTRAÍDO! Serviço: '{servico}'")
        print(f"✅ Estado avançou: {ctx.get('estado_fluxo')}")
        return True
    else:
        print(f"❌ MANICURE NÃO EXTRAÍDO")
        print(f"❌ Estado não avançou: {ctx.get('estado_fluxo')}")
        return False

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
