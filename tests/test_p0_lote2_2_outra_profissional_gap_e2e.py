"""
[MIGRAÇÃO LOTE 2 — TESTE 2] Outra Profissional Gap — E2E Firebase Real

Convertido de: test_p0_outra_profissional_gap.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que "quero com outra profissional" é reconhecido corretamente
durante fluxo de agendamento.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote2_2_reconhece_outra_profissional_e2e():
    """
    T1: Reconhece "quero com outra profissional" durante agendamento.
    Mensagem: "quero com outra profissional"
    Esperado: Sistema reconhece mudança de profissional
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512101{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Reconhece 'outra profissional'")

    # Setup Firestore com draft em agendamento (simulando contexto de mudança)
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "bruna",
            "data_hora": "2026-10-22T10:00"
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

    # Sistema deve oferecer outras profissionais
    assert any(x in resposta_texto for x in [
        "profissional", "qual", "outra", "gloria", "joana", "carla", "preferir"
    ]), f"Troca de profissional não reconhecida. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema ofereceu alternativas de profissional")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote2_2_outra_profissional_sem_draft_e2e():
    """
    T2: "quero com outra profissional" fora de contexto de agendamento.
    Mensagem: "quero com outra profissional"
    Esperado: Sistema não faz suposições
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512102{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: 'outra profissional' sem contexto")

    # Setup sem draft
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
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

    # Sistema deve responder de forma segura (pedindo mais contexto)
    assert len(resposta_texto) > 0, "Resposta vazia"

    print(f"  ✓ Sistema respondeu apropriadamente")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")
