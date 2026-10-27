"""
[P0.3.1] Teste E2E WEBHOOK REAL — Reproduzir Erro Exato

Objetivo:
Reproduzir o erro EXATO que o usuário viu:
[P0626_VALIDACAO] Serviço inexistente: corte feminino

Estratégia:
1. Chamar o endpoint `/webhook/whatsapp` REAL (Flask)
2. Usar Firestore REAL (não mock)
3. Passar 3 mensagens idênticas ao fluxo do usuário
4. Sem validação HMAC (teste local)
5. DEVE reproduzir: [P0626_VALIDACAO] Serviço inexistente

Diferença do teste anterior:
- Usa o endpoint Flask real `/webhook/whatsapp`
- Payload usa o formato REAL do webhook do WhatsApp
- Vai até criar evento (não para antes)
"""

import pytest
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

# Mock do scheduler antes de importar main
with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from services.firebase_service_async import deletar_dado_em_path
from utils.contexto_temporario import carregar_contexto_temporario_v2

TENANT_TESTE = "7394370553"
USUARIO_NUMERO = "5511991382080"
ENDPOINT_TESTE = "1350170954840548"


@pytest.mark.asyncio
async def test_webhook_real_reproduz_erro_p0626():
    """
    [E2E WEBHOOK REAL] Reproduz erro [P0626_VALIDACAO]

    Fluxo REAL do usuário:
    1. MSG 1: "voce tem agenda para corte amanha as 10?" → classifica + extrai servico
    2. MSG 2: "com gloria" → escolhe profissional
    3. MSG 3: "esta sim, pode confirmar" → ERRO: Serviço vazio na validação
    """

    print("\n" + "="*100)
    print("TESTE E2E WEBHOOK REAL — Reproduzir [P0626_VALIDACAO]")
    print("="*100)
    print(f"\nSetup:")
    print(f"  Tenant: {TENANT_TESTE}")
    print(f"  Endpoint: {ENDPOINT_TESTE}")
    print(f"  Usuário: {USUARIO_NUMERO}")
    print(f"  Firestore: REAL (não mock)")
    print(f"  Webhook: REAL (Flask /webhook/whatsapp)")

    client = app.test_client()

    # ========================================================================
    # LIMPEZA: Deletar contexto anterior
    # ========================================================================

    print(f"\n[LIMPEZA] Deletar contexto anterior")
    try:
        path_novo = f"Clientes/{TENANT_TESTE}/Sessoes/whatsapp:{USUARIO_NUMERO}"
        await deletar_dado_em_path(path_novo)
        print(f"  ✅ Deletado: {path_novo}")
    except:
        print(f"  ℹ️  Path novo vazio")

    try:
        path_legado = f"Clientes/{TENANT_TESTE}/Sessoes/{USUARIO_NUMERO}"
        await deletar_dado_em_path(path_legado)
        print(f"  ✅ Deletado: {path_legado}")
    except:
        print(f"  ℹ️  Path legado vazio")

    # ========================================================================
    # MSG 1: Consulta Inicial
    # ========================================================================

    print(f"\n[MSG 1] Webhook: 'voce tem agenda para corte amanha as 10?'")

    timestamp_1 = int(time.time() * 1000)
    msg_id_1 = f"wamid.test_real_{timestamp_1}_msg1"

    # Payload REAL do WhatsApp
    payload_1 = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5519994443694",
                        "phone_number_id": ENDPOINT_TESTE
                    },
                    "contacts": [{
                        "profile": {"name": "Anderson"},
                        "wa_id": USUARIO_NUMERO
                    }],
                    "messages": [{
                        "from": USUARIO_NUMERO,
                        "id": msg_id_1,
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
        response_1 = client.post(
        "/webhook/whatsapp",
        json=payload_1,
        headers={"Content-Type": "application/json"}
    )

    print(f"  Status: {response_1.status_code}")
    if response_1.status_code != 200:
        print(f"  ❌ FALHA: {response_1.data}")
        # Tenta sem validação
        with patch("main.validar_assinatura_whatsapp", return_value=True):
            with patch("main.validate_whatsapp_signature", return_value=True):
                response_1 = client.post(
                    "/webhook/whatsapp",
                    json=payload_1,
                    headers={"Content-Type": "application/json"}
                )
                print(f"  Tentou sem HMAC: {response_1.status_code}")

    assert response_1.status_code == 200, f"MSG 1 falhou: {response_1.data}"
    print(f"  ✅ Processada")

    await asyncio.sleep(1.0)

    # Validar contexto
    ctx_1 = await carregar_contexto_temporario_v2(TENANT_TESTE, f"whatsapp:{USUARIO_NUMERO}")
    print(f"  Contexto após MSG 1:")
    print(f"    servico: {ctx_1.get('servico')}")
    print(f"    data_hora: {ctx_1.get('data_hora')}")
    print(f"    estado_fluxo: {ctx_1.get('estado_fluxo')}")

    # ========================================================================
    # MSG 2: Escolher Profissional
    # ========================================================================

    print(f"\n[MSG 2] Webhook: 'com gloria'")

    timestamp_2 = int(time.time() * 1000)
    msg_id_2 = f"wamid.test_real_{timestamp_2}_msg2"

    payload_2 = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5519994443694",
                        "phone_number_id": ENDPOINT_TESTE
                    },
                    "contacts": [{
                        "profile": {"name": "Anderson"},
                        "wa_id": USUARIO_NUMERO
                    }],
                    "messages": [{
                        "from": USUARIO_NUMERO,
                        "id": msg_id_2,
                        "timestamp": str(int(time.time())),
                        "text": {"body": "com gloria"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    response_2 = client.post(
        "/webhook/whatsapp",
        json=payload_2,
        headers={"Content-Type": "application/json"}
    )

    print(f"  Status: {response_2.status_code}")
    assert response_2.status_code == 200, f"MSG 2 falhou: {response_2.data}"
    print(f"  ✅ Processada")

    await asyncio.sleep(1.0)

    # ========================================================================
    # MSG 3: Confirmação (AQUI DEVE REPRODUZIR O ERRO)
    # ========================================================================

    print(f"\n[MSG 3] Webhook: 'esta sim, pode confirmar'")
    print(f"  ⚠️  ESPERADO: [P0626_VALIDACAO] Serviço inexistente: corte feminino")

    timestamp_3 = int(time.time() * 1000)
    msg_id_3 = f"wamid.test_real_{timestamp_3}_msg3"

    payload_3 = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5519994443694",
                        "phone_number_id": ENDPOINT_TESTE
                    },
                    "contacts": [{
                        "profile": {"name": "Anderson"},
                        "wa_id": USUARIO_NUMERO
                    }],
                    "messages": [{
                        "from": USUARIO_NUMERO,
                        "id": msg_id_3,
                        "timestamp": str(int(time.time())),
                        "text": {"body": "esta sim, pode confirmar"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    response_3 = client.post(
        "/webhook/whatsapp",
        json=payload_3,
        headers={"Content-Type": "application/json"}
    )

    print(f"  Status: {response_3.status_code}")
    assert response_3.status_code == 200, f"MSG 3 falhou: {response_3.data}"
    print(f"  ✅ Processada")

    print(f"\n  ⚠️  VERIFIQUE OS LOGS ACIMA PARA:")
    print(f"      [P0626_VALIDACAO] Serviço inexistente: corte feminino")
    print(f"\n  SE NÃO APARECEU, O ERRO ESTÁ EM ALGUM LUGAR DOS LOGS ACIMA!")

    await asyncio.sleep(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
