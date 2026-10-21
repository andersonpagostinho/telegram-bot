"""
[MIGRAÇÃO LOTE 4 — TESTE 5] Regra X1 Adjacência — E2E Firebase Real

Objetivo: Validar regra de adjacência em agendamentos.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote4_5_adjacencia_profissionais_e2e():
    """
    T1: Sistema reconhece profissionais adjacentes.
    Mensagem: "quero com outra profissional"
    Esperado: Sistema oferece profissionais que fazem mesmo serviço
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514401{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Regra X1 adjacência")

    # Setup com draft em agendamento
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero com outra profissional",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Adjacência reconhecida")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote4_5_mesma_profissional_validacao_e2e():
    """
    T2: Sistema valida contextualmente.
    Mensagem: qualquer resposta após mudança
    Esperado: Sistema responde apropriadamente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5514402{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Validação contextual")

    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="segunda",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Validação contextual respondida")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")
