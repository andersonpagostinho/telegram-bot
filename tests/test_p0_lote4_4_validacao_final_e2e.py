"""
[MIGRAÇÃO LOTE 4 — TESTE 4] Validação Final P04 — E2E Firebase Real

Objetivo: Validação final de P04 antes de produção.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote4_4_fluxo_sem_erros_e2e():
    """
    T1: Fluxo completo não produz erros.
    Mensagem: Sequência de mensagens do agendamento
    Esperado: Nenhum erro ou exceção
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514301{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Fluxo sem erros")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Sequência de mensagens
    mensagens = ["oi", "quero agendar", "corte", "segunda", "bruna"]

    for msg in mensagens:
        resposta = await roteador_principal(
            user_id=phone_number,
            mensagem=msg,
            tenant_id=E2E_TENANT_ID,
            phone_number_id="1350170954840548",
        )
        assert len(resposta.get("resposta", "")) > 0, f"Resposta vazia para '{msg}'"

    print(f"  ✓ Fluxo completo sem erros")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote4_4_contexto_persistente_e2e():
    """
    T2: Contexto persiste sem corrupção.
    Esperado: Dados não se perdem entre mensagens
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514302{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Contexto persistente")

    ctx_inicial = {"tipo_usuario": "cliente", "estado_fluxo": "idle"}
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Primeira mensagem
    resposta1 = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    ctx1 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    tipo1 = ctx1.get("tipo_usuario")

    # Segunda mensagem
    resposta2 = await roteador_principal(
        user_id=phone_number,
        mensagem="corte",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    ctx2 = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    tipo2 = ctx2.get("tipo_usuario")

    # Tipo_usuario não deve mudar
    assert tipo1 == tipo2, "Contexto foi corrompido entre mensagens"

    print(f"  ✓ Contexto persistente sem corrupção")
    print(f"  ✅ [T2] PASS")
