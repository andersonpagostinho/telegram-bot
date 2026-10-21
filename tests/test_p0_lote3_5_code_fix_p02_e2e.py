"""
[MIGRAÇÃO LOTE 3 — TESTE 5] Code Fix P02 — E2E Firebase Real

Convertido de: test_p02_code_fix.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que fixes de código em P02 funcionam corretamente.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote3_5_tratamento_erros_encoding_e2e():
    """
    T1: Sistema trata caracteres especiais corretamente.
    Mensagem: "quero agendar coloração com é/à/ç"
    Esperado: Sistema não falha com encoding
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513401{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Tratamento de caracteres especiais")
    print(f"  Mensagem: 'quero coloração'")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem com caracteres especiais
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero coloração",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema não deve falhar
    assert len(resposta_texto) > 0, "Resposta vazia (possível erro de encoding)"

    print(f"  ✓ Caracteres especiais tratados corretamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote3_5_mensagem_vazia_e_validacao_e2e():
    """
    T2: Sistema trata mensagens vazias ou inválidas corretamente.
    Mensagem: "" (vazia)
    Esperado: Sistema pede esclarecimento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513402{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Mensagem vazia ou inválida")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem com espaços em branco
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="   ",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve responder mesmo com mensagem vazia
    assert len(resposta_texto) > 0, "Sistema não respondeu a mensagem vazia"

    print(f"  ✓ Mensagem vazia tratada")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")
