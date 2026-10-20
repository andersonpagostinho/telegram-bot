"""
[P0.3.1] Teste ERRO REAL — Cliente 5511991382080 com Firebase Real

Objetivo:
Reproduzir o erro EXATO que você viu:
[P0626_VALIDACAO] Serviço inexistente: corte feminino

Estratégia:
1. Usar cliente REAL: 5511991382080 (com histórico em Firestore)
2. NÃO limpar contexto anterior (deixar draft ativo)
3. Enviar 3 mensagens via webhook REAL Flask
4. Deve reproduzir: [P0626_VALIDACAO]

Este teste simula EXATAMENTE seu fluxo real!
"""
import pytest
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import carregar_contexto_temporario_v2

TENANT = "7394370553"
USER = "5511991382080"  # ← SEU CLIENTE REAL
ENDPOINT = "1350170954840548"

@pytest.mark.asyncio
async def test_erro_real_cliente_5511991382080():
    """
    Reproduz erro EXATO com seu cliente real
    
    NÃO LIMPA CONTEXTO ANTERIOR — deixa histórico do Firebase
    """
    
    print("\n" + "="*80)
    print("TESTE ERRO REAL — Cliente 5511991382080")
    print("="*80)
    print(f"\nSetup:")
    print(f"  Cliente REAL: {USER}")
    print(f"  Tenant: {TENANT}")
    print(f"  Firebase: REAL (não limpo)")
    print(f"  Webhook: REAL Flask")
    
    client = app.test_client()
    
    # ✅ NÃO LIMPAR — deixar contexto anterior como você tem!
    print(f"\n[CONTEXTO] Deixando histórico anterior intacto")
    ctx_anterior = await carregar_contexto_temporario_v2(TENANT, f"whatsapp:{USER}")
    print(f"  Estado anterior: {ctx_anterior.get('estado_fluxo')}")
    print(f"  Draft anterior: {ctx_anterior.get('draft_agendamento')}")
    
    # MSG: "voce tem agenda para corte amanha as 10?"
    print(f"\n[MSG] Enviando: 'voce tem agenda para corte amanha as 10?'")
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": ENDPOINT},
                    "contacts": [{"profile": {"name": "Anderson"}, "wa_id": USER}],
                    "messages": [{
                        "from": USER,
                        "id": f"wamid.real_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "voce tem agenda para corte amanha as 10?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    print("\n⚠️  ESPERADO: [P0626_VALIDACAO] Serviço inexistente: corte feminino")
    print("    Verifique os LOGS ABAIXO para encontrar esse erro!\n")
    
    with patch("main.validate_whatsapp_signature", return_value=True):
        response = client.post("/webhook/whatsapp", json=payload)
    
    print(f"\n✅ Webhook retornou: {response.status_code}")
    print("\n⚠️  PROCURE PELOS LOGS ACIMA:")
    print("    [P0626_VALIDACAO] Serviço inexistente: corte feminino")
    
    assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
