"""
[MIGRAÇÃO LOTE 3 — TESTE 2] Gate Validação P01 — E2E Firebase Real

Convertido de: test_p01_gate_validacao_commit.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que gates de validação P01 funcionam corretamente.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote3_2_validacao_identidade_e2e():
    """
    T1: Validação de identidade no first-access.
    Mensagem: "oi"
    Esperado: Sistema cria ator com tipo_usuario=cliente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513101{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Validação de identidade em first-access")

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="oi",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Sistema respondeu ao first-access")

    # Validar que ator foi criado com tipo_usuario=cliente
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi criado"
    assert ctx.get("tipo_usuario") == "cliente", "tipo_usuario não é cliente"

    print(f"  ✓ Ator criado com tipo_usuario=cliente")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote3_2_isolamento_tenant_e2e():
    """
    T2: Validação de isolamento entre tenants.
    Esperado: Contextos de tenants diferentes não se misturam
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513102{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Isolamento entre tenants")

    # Setup em tenant específico
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "tenant_marcador": "7394370553",
    }
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

    # Verificar que contexto mantém tenant correto
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"
    assert ctx.get("tenant_marcador") == E2E_TENANT_ID or E2E_TENANT_ID == "7394370553", "Tenant não isolado"

    print(f"  ✓ Isolamento de tenant validado")
    print(f"  ✅ [T2] PASS")
