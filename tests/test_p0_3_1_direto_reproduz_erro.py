"""
[P0.3.1] Teste DIRETO — Chamar Handler Sem Flask/HMAC

Objetivo:
Reproduzir o erro exato:
[P0626_VALIDACAO] Serviço inexistente: corte feminino

Estratégia:
1. Chamar o handler processar_mensagem_whatsapp DIRETAMENTE
2. Usar Firestore REAL
3. Simular 3 mensagens exatas que causam o erro
"""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from unittest.mock import AsyncMock, patch
from handlers.whatsapp_bridge_handler import processar_mensagem_whatsapp
from utils.contexto_temporario import carregar_contexto_temporario_v2
from services.firebase_service_async import deletar_dado_em_path

TENANT_TESTE = "7394370553"
USUARIO_NUMERO = "5511991382080"
ACTOR_ID = f"whatsapp:{USUARIO_NUMERO}"
NEOEVE_NUMBER = "5519994443694"


@pytest.mark.asyncio
async def test_direto_reproduz_erro_servico():
    """
    Reproduz erro chamando handler DIRETAMENTE

    Fluxo:
    1. MSG 1: "voce tem agenda para corte amanha as 10?" → servico="corte feminino"
    2. MSG 2: "com gloria" → escolhe profissional
    3. MSG 3: "esta sim, pode confirmar" → ERRO: Serviço vazio na validação

    O erro acontece porque em algum ponto do fluxo de criação de evento,
    o contexto é carregado de um path LEGADO vazio em vez do novo.
    """

    print("\n" + "="*100)
    print("TESTE DIRETO — Reproduzir Erro [P0626_VALIDACAO]")
    print("="*100)

    # Limpeza
    print("\n[LIMPEZA] Deletar contextos anteriores")
    try:
        path = f"Clientes/{TENANT_TESTE}/Sessoes/{ACTOR_ID}"
        await deletar_dado_em_path(path)
        print(f"  ✅ Contexto deletado: {path}")
    except Exception as e:
        print(f"  ℹ️  Nenhum contexto anterior")

    # ========================================================================
    # MSG 1: Consulta Determinística
    # ========================================================================

    print(f"\n[MSG 1] Enviar: 'voce tem agenda para corte amanha as 10?'")

    payload_1 = {
        "canal": "whatsapp",
        "tenant_id": TENANT_TESTE,
        "neoeve_number": NEOEVE_NUMBER,
        "actor_id": ACTOR_ID,
        "texto": "voce tem agenda para corte amanha as 10?"
    }

    with patch("services.whatsapp_service.enviar_mensagem_whatsapp", new_callable=AsyncMock):
        resultado_1 = await processar_mensagem_whatsapp(payload_1)

    print(f"  ✅ MSG 1 processada")
    await asyncio.sleep(0.5)

    # Validar contexto após MSG 1
    ctx_1 = await carregar_contexto_temporario_v2(TENANT_TESTE, ACTOR_ID)
    print(f"  Contexto após MSG 1:")
    print(f"    servico: {ctx_1.get('servico')}")
    print(f"    data_hora: {ctx_1.get('data_hora')}")
    print(f"    estado_fluxo: {ctx_1.get('estado_fluxo')}")

    assert ctx_1.get("servico") == "corte feminino", \
        f"❌ Serviço não extraído: {ctx_1.get('servico')}"
    print(f"  ✅ Serviço extraído corretamente")

    # ========================================================================
    # MSG 2: Escolher Profissional
    # ========================================================================

    print(f"\n[MSG 2] Enviar: 'com gloria'")

    payload_2 = {
        "canal": "whatsapp",
        "tenant_id": TENANT_TESTE,
        "neoeve_number": NEOEVE_NUMBER,
        "actor_id": ACTOR_ID,
        "texto": "com gloria"
    }

    with patch("services.whatsapp_service.enviar_mensagem_whatsapp", new_callable=AsyncMock):
        resultado_2 = await processar_mensagem_whatsapp(payload_2)

    print(f"  ✅ MSG 2 processada")
    await asyncio.sleep(0.5)

    # ========================================================================
    # MSG 3: Confirmação (AQUI DEVE REPRODUZIR O ERRO)
    # ========================================================================

    print(f"\n[MSG 3] Enviar: 'esta sim, pode confirmar'")
    print(f"  ⚠️  ESPERADO: [P0626_VALIDACAO] Serviço inexistente: corte feminino")

    payload_3 = {
        "canal": "whatsapp",
        "tenant_id": TENANT_TESTE,
        "neoeve_number": NEOEVE_NUMBER,
        "actor_id": ACTOR_ID,
        "texto": "esta sim, pode confirmar"
    }

    with patch("services.whatsapp_service.enviar_mensagem_whatsapp", new_callable=AsyncMock):
        resultado_3 = await processar_mensagem_whatsapp(payload_3)

    print(f"  ✅ MSG 3 processada")
    print(f"\n  ⚠️  VERIFIQUE OS LOGS ACIMA PARA:")
    print(f"      [P0626_VALIDACAO] Serviço inexistente: corte feminino")
    print(f"\n  O ERRO DEVE ESTAR EM ALGUM LUGAR ACIMA!")

    await asyncio.sleep(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
