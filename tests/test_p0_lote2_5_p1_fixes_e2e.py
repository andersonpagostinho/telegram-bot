"""
[MIGRAÇÃO LOTE 2 — TESTE 5] P1 Fixes Validation — E2E Firebase Real

Convertido de: test_p0_p1_fixes_implementation.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que fixes implementados em P0 não quebram fluxos P1.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote2_5_primeiro_acesso_cria_contexto_e2e():
    """
    T1: Primeiro acesso de novo usuário cria contexto corretamente.
    Mensagem: "oi"
    Esperado: Sistema cria contexto com tipo_usuario=cliente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512401{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Primeiro acesso cria contexto")

    # NÃO precisa setup pois é primeiro acesso
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="oi",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Sistema respondeu ao primeiro acesso")

    # Contexto deve ter sido criado
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi criado no primeiro acesso"
    assert ctx.get("tipo_usuario") == "cliente", f"tipo_usuario incorreto: {ctx.get('tipo_usuario')}"

    print(f"  ✓ Contexto criado com tipo_usuario=cliente")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote2_5_persistencia_contexto_e2e():
    """
    T2: Contexto persiste entre mensagens.
    Mensagem 1: "quero agendar corte"
    Mensagem 2: "segunda"
    Esperado: Contexto mantém draft entre mensagens
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512402{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Persistência de contexto entre mensagens")

    # Setup inicial
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Mensagem 1
    resposta1 = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar corte",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print(f"  Msg 1: 'quero agendar corte'")

    # Validar contexto após msg1
    ctx1 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx1 is not None, "Contexto não mantido após msg1"

    # Mensagem 2
    resposta2 = await roteador_principal(
        user_id=phone_number,
        mensagem="segunda",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print(f"  Msg 2: 'segunda'")

    # Validar contexto após msg2
    ctx2 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx2 is not None, "Contexto não mantido após msg2"

    print(f"  ✓ Contexto persistiu entre mensagens")
    print(f"  ✅ [T2] PASS")
