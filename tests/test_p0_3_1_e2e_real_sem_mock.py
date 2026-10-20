"""
[P0.3.1] Teste E2E REAL — Webhook Flask + Firebase Real (SEM MOCK)

Objetivo:
Reproduzir o erro exato que o usuário viu:
[P0626_VALIDACAO] Serviço inexistente: corte feminino

Fluxo:
1. MSG 1: "voce tem agenda para corte amanha as 10?" → Classificação + Extração
2. MSG 2: "com gloria" → Escolhe profissional
3. MSG 3: "esta sim, pode confirmar" → Tenta criar evento
4. ERRO: Serviço vazio na validação

Restrições:
- Sem mock de WhatsApp (envio real)
- Sem mock de Firebase (leitura/escrita real)
- Flask test_client (endpoint real, não chamada direta)
- 100% rastreável
"""

import pytest
import sys
import json
import hmac
import hashlib
import time
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurar ambiente
import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

# Mock do scheduler antes de importar main
with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from services.firebase_service_async import buscar_dado_em_path, deletar_dado_em_path
from utils.contexto_temporario import carregar_contexto_temporario_v2

# Cliente real com agendamento ativo
TENANT_TESTE = "7394370553"
USUARIO_NUMERO = "5511991382080"
ENDPOINT_TESTE = "1350170954840548"


def gerar_hmac_signature(body_str: str, secret: str = "") -> str:
    """Gera assinatura HMAC válida para payload"""
    hash_value = hmac.new(
        secret.encode(),
        body_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={hash_value}"


@pytest.mark.asyncio
async def test_e2e_real_reproduzir_erro_servico():
    """
    [E2E REAL] Reproduz o erro exato: Serviço vazio na criação de evento

    Esperado:
    ❌ [P0626_VALIDACAO] Serviço inexistente: corte feminino
    """

    print("\n" + "="*100)
    print("TESTE E2E REAL — Reproduzir Erro de Validação de Serviço")
    print("="*100)
    print(f"\nSetup:")
    print(f"  Tenant: {TENANT_TESTE}")
    print(f"  Endpoint: {ENDPOINT_TESTE}")
    print(f"  Usuário: {USUARIO_NUMERO}")

    client = app.test_client()

    # ========================================================================
    # LIMPEZA: Deletar contexto anterior
    # ========================================================================

    print(f"\n[LIMPEZA] Deletar contexto anterior")
    from services.firebase_service_async import deletar_dado_em_path
    path_novo = f"Clientes/{TENANT_TESTE}/Sessoes/whatsapp:{USUARIO_NUMERO}"
    path_legado = f"Clientes/{TENANT_TESTE}/Sessoes/{USUARIO_NUMERO}"

    try:
        await deletar_dado_em_path(path_novo)
        print(f"  ✅ Path novo deletado: {path_novo}")
    except Exception as e:
        print(f"  ℹ️  Path novo vazio: {e}")

    try:
        await deletar_dado_em_path(path_legado)
        print(f"  ✅ Path legado deletado: {path_legado}")
    except Exception as e:
        print(f"  ℹ️  Path legado vazio: {e}")

    # ========================================================================
    # MSG 1: Consulta
    # ========================================================================

    print(f"\n[MSG 1] Enviar: 'voce tem agenda para corte amanha as 10?'")

    timestamp_1 = int(time.time() * 1000)
    msg_id_1 = f"wamid.test_real_{timestamp_1}_msg1"

    payload_1 = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": ENDPOINT_TESTE,
                        "display_phone_number": f"+55 11 {USUARIO_NUMERO[4:]}",
                        "business_account_id": "test_waba_999"
                    },
                    "messages": [{
                        "id": msg_id_1,
                        "from": USUARIO_NUMERO,
                        "text": {"body": "voce tem agenda para corte amanha as 10?"},
                        "type": "text"
                    }]
                }
            }]
        }]
    }

    # Não enviar assinatura para teste local (Flask test_client não valida)
    response_1 = client.post(
        "/webhook/whatsapp",
        json=payload_1
    )

    assert response_1.status_code == 200, f"MSG 1 FALHOU: {response_1.data}"
    print(f"  ✅ Status: {response_1.status_code}")

    await asyncio.sleep(1.0)

    # Validar contexto após MSG 1
    ctx_1 = await carregar_contexto_temporario_v2(TENANT_TESTE, f"whatsapp:{USUARIO_NUMERO}")
    print(f"  Contexto após MSG 1:")
    print(f"    servico: {ctx_1.get('servico')}")
    print(f"    data_hora: {ctx_1.get('data_hora')}")
    print(f"    estado_fluxo: {ctx_1.get('estado_fluxo')}")

    assert ctx_1.get("servico"), f"❌ Serviço não extraído em MSG 1: {ctx_1.get('servico')}"
    print(f"  ✅ Serviço extraído: {ctx_1.get('servico')}")

    # ========================================================================
    # MSG 2: Escolher profissional
    # ========================================================================

    print(f"\n[MSG 2] Enviar: 'com gloria'")

    timestamp_2 = int(time.time() * 1000)
    msg_id_2 = f"wamid.test_real_{timestamp_2}_msg2"

    payload_2 = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": ENDPOINT_TESTE,
                        "display_phone_number": f"+55 11 {USUARIO_NUMERO[4:]}",
                        "business_account_id": "test_waba_999"
                    },
                    "messages": [{
                        "id": msg_id_2,
                        "from": USUARIO_NUMERO,
                        "text": {"body": "com gloria"},
                        "type": "text"
                    }]
                }
            }]
        }]
    }

    response_2 = client.post(
        "/webhook/whatsapp",
        json=payload_2
    )

    assert response_2.status_code == 200, f"MSG 2 FALHOU: {response_2.data}"
    print(f"  ✅ Status: {response_2.status_code}")

    await asyncio.sleep(1.0)

    # Validar contexto após MSG 2
    ctx_2 = await carregar_contexto_temporario_v2(TENANT_TESTE, f"whatsapp:{USUARIO_NUMERO}")
    print(f"  Contexto após MSG 2:")
    print(f"    servico: {ctx_2.get('servico')}")
    print(f"    profissional_escolhido: {ctx_2.get('profissional_escolhido')}")
    print(f"    estado_fluxo: {ctx_2.get('estado_fluxo')}")

    # ========================================================================
    # MSG 3: Confirmação (AQUI DEVE FALHAR COM ERRO DE SERVIÇO)
    # ========================================================================

    print(f"\n[MSG 3] Enviar: 'esta sim, pode confirmar'")
    print(f"  ⚠️  ESPERADO: [P0626_VALIDACAO] Serviço inexistente: corte feminino")

    timestamp_3 = int(time.time() * 1000)
    msg_id_3 = f"wamid.test_real_{timestamp_3}_msg3"

    payload_3 = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": ENDPOINT_TESTE,
                        "display_phone_number": f"+55 11 {USUARIO_NUMERO[4:]}",
                        "business_account_id": "test_waba_999"
                    },
                    "messages": [{
                        "id": msg_id_3,
                        "from": USUARIO_NUMERO,
                        "text": {"body": "esta sim, pode confirmar"},
                        "type": "text"
                    }]
                }
            }]
        }]
    }

    response_3 = client.post(
        "/webhook/whatsapp",
        json=payload_3
    )

    assert response_3.status_code == 200, f"MSG 3 FALHOU: {response_3.data}"
    print(f"  ✅ Status: {response_3.status_code}")
    print(f"\n  ⚠️  Verifique os LOGS acima para encontrar:")
    print(f"      [P0626_VALIDACAO] Serviço inexistente: corte feminino")

    await asyncio.sleep(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
