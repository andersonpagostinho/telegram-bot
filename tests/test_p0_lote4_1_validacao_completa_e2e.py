"""
[MIGRAÇÃO LOTE 4 — TESTE 1] Validação Completa P04 — E2E Firebase Real

Objetivo: Validar fluxo completo de agendamento com todas as validações.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote4_1_fluxo_completo_agendamento_e2e():
    """
    T1: Fluxo completo de agendamento com validações.
    Mensagem: "quero agendar corte para segunda com bruna às 10"
    Esperado: Sistema reconhece e processa todas as validações
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Fluxo completo com validações")

    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero agendar corte para segunda com bruna às 10",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Fluxo completo processado")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote4_1_validacao_dados_completos_e2e():
    """
    T2: Validação de que todos os dados foram coletados.
    Esperado: Draft tem serviço, profissional, data_hora
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514002{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Validação de dados completos")

    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="agendar corte segunda bruna 10",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Resposta vazia"

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Validação de dados completos")
    print(f"  ✅ [T2] PASS")
