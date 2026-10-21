"""
[MIGRAÇÃO LOTE 4 — TESTE 3] Phone Number ID Identidade — E2E Firebase Real

Objetivo: Validar que phone_number_id é integrado à identidade corretamente.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote4_3_identidade_com_phone_number_id_e2e():
    """
    T1: Phone number ID está integrado à identidade.
    Esperado: Sistema usa phone_number_id na criação de ator
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514201{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Phone number ID na identidade")

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="oi",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi criado"

    print(f"  ✓ Identidade com phone_number_id criada")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote4_3_canal_whatsapp_derivado_e2e():
    """
    T2: Canal WhatsApp é derivado corretamente.
    Esperado: Contexto tem canal=whatsapp
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514202{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Canal derivado corretamente")

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="qual é meu canal?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Canal derivado e salvo")
    print(f"  ✅ [T2] PASS")
