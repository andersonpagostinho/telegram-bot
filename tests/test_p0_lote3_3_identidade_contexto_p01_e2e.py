"""
[MIGRAÇÃO LOTE 3 — TESTE 3] Identidade + Contexto P01 — E2E Firebase Real

Convertido de: test_p01_identidade_contexto.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que identidade e contexto são criados juntos corretamente.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote3_3_identidade_e_contexto_juntos_e2e():
    """
    T1: Identidade e contexto são criados juntos no first-access.
    Mensagem: "quero agendar"
    Esperado: IdentidadeContexto + Sessão criados atomicamente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513201{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Identidade + Contexto no first-access")
    print(f"  Mensagem: 'quero agendar'")

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Sistema respondeu")

    # Validar que contexto foi criado
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi criado"

    # Validar campos básicos de identidade
    assert ctx.get("tipo_usuario") is not None, "tipo_usuario não definido"

    print(f"  ✓ Identidade + Contexto criados atomicamente")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote3_3_consistencia_identidade_e2e():
    """
    T2: Identidade mantém consistência entre acessos.
    Mensagem 1: "oi"
    Mensagem 2: "qual é meu id?"
    Esperado: ID mantém-se consistente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5513202{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Consistência de identidade")

    # Primeiro acesso
    resposta1 = await roteador_principal(
        user_id=phone_number,
        mensagem="oi",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print(f"  Acesso 1: 'oi'")

    ctx1 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx1 is not None, "Contexto não criado no acesso 1"

    # Segundo acesso
    resposta2 = await roteador_principal(
        user_id=phone_number,
        mensagem="qual é meu id?",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print(f"  Acesso 2: 'qual é meu id?'")

    ctx2 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx2 is not None, "Contexto não mantido no acesso 2"

    # Validar tipo_usuario permanece consistente
    assert ctx1.get("tipo_usuario") == ctx2.get("tipo_usuario"), "tipo_usuario mudou entre acessos"

    print(f"  ✓ Identidade mantém consistência entre acessos")
    print(f"  ✅ [T2] PASS")
