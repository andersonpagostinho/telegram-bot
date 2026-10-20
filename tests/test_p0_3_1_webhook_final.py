"""
[P0.3.1] Teste WEBHOOK FINAL — Reproduzir erro [P0626_VALIDACAO]
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

from services.firebase_service_async import deletar_dado_em_path
from utils.contexto_temporario import carregar_contexto_temporario_v2

TENANT = "7394370553"
USER = "5511991382080"
ENDPOINT = "1350170954840548"

@pytest.mark.asyncio
async def test_webhook_reproduz_p0626():
    """Reproduz [P0626_VALIDACAO] Serviço inexistente"""
    
    print("\n" + "="*80)
    print("TESTE WEBHOOK — Reproduzir [P0626_VALIDACAO]")
    print("="*80)
    
    client = app.test_client()
    
    # Limpar
    try:
        await deletar_dado_em_path(f"Clientes/{TENANT}/Sessoes/whatsapp:{USER}")
    except:
        pass
    
    # MSG 1
    print("\n[MSG 1] 'voce tem agenda para corte amanha as 10?'")
    payload_1 = {
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
                        "id": f"wamid.test_{int(time.time() * 1000)}_msg1",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "voce tem agenda para corte amanha as 10?"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    with patch("main.validate_whatsapp_signature", return_value=True):
        r1 = client.post("/webhook/whatsapp", json=payload_1)
    assert r1.status_code == 200
    print("  ✅ Processada")
    await asyncio.sleep(1)
    
    # MSG 2
    print("[MSG 2] 'com gloria'")
    payload_2 = {
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
                        "id": f"wamid.test_{int(time.time() * 1000)}_msg2",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "com gloria"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    with patch("main.validate_whatsapp_signature", return_value=True):
        r2 = client.post("/webhook/whatsapp", json=payload_2)
    assert r2.status_code == 200
    print("  ✅ Processada")
    await asyncio.sleep(1)
    
    # MSG 3 — DEVE REPRODUZIR ERRO
    print("[MSG 3] 'esta sim, pode confirmar'")
    print("  ⚠️  ESPERADO: [P0626_VALIDACAO] Serviço inexistente")
    payload_3 = {
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
                        "id": f"wamid.test_{int(time.time() * 1000)}_msg3",
                        "timestamp": str(int(time.time())),
                        "text": {"body": "esta sim, pode confirmar"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    with patch("main.validate_whatsapp_signature", return_value=True):
        r3 = client.post("/webhook/whatsapp", json=payload_3)
    assert r3.status_code == 200
    print("  ✅ Processada")
    
    print("\n  ⚠️  VERIFIQUE OS LOGS ACIMA PARA [P0626_VALIDACAO]!")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
