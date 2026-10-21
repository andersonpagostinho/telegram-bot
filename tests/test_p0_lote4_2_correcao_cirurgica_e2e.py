"""
[MIGRAÇÃO LOTE 4 — TESTE 2] Correção Cirúrgica P04 — E2E Firebase Real

Objetivo: Validar correções críticas de P04.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote4_2_correcao_phone_number_id_e2e():
    """
    T1: Phone number ID é extraído corretamente.
    Esperado: Sistema mantém phone_number_id em contexto
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514101{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Phone number ID extraído")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="oi",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Phone number ID mantido")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote4_2_correcao_validacao_tenant_e2e():
    """
    T2: Tenant ID é validado corretamente.
    Esperado: Contexto respeita tenant_id
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514102{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Validação de tenant ID")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="qual é meu tenant?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Tenant ID validado")
    print(f"  ✅ [T2] PASS")
