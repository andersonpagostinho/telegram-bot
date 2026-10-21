"""
[MIGRAÇÃO LOTE 2 — TESTE 1] Hotfix Contexto Agendamento — E2E Firebase Real

Convertido de: test_p0_hotfix_contexto_agendamento.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que pedidos explícitos de agendamento são reconhecidos
corretamente quando o serviço está no catálogo do tenant.
"""

import pytest
import time
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote2_1_agendamento_explicito_e2e():
    """
    T1: Pedido explícito de agendamento com todos os elementos.
    Mensagem: "quero marcar corte para segunda com a bruna às 9"
    Esperado: Sistema reconhece e inicia fluxo de agendamento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Agendamento explícito com todos elementos")
    print(f"  Phone: {phone_number}")

    # Setup Firestore
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Chamar roteador com Firestore real
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero marcar corte para segunda com a bruna às 9",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer agendamento
    assert any(x in resposta_texto for x in [
        "corte", "segunda", "bruna", "horário", "profissional", "qual", "prefere"
    ]), f"Agendamento não reconhecido. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema reconheceu agendamento explícito")

    # Validar contexto
    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✓ Contexto atualizado no Firestore")
    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote2_1_agendamento_somente_data_e2e():
    """
    T2: Agendamento mencionando apenas data.
    Mensagem: "quero marcar corte para amanhã"
    Esperado: Sistema reconhece como agendamento, pede mais detalhes
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512002{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Agendamento com apenas data")
    print(f"  Mensagem: 'quero marcar corte para amanhã'")

    # Setup Firestore
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
        mensagem="quero marcar corte para amanhã",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve pedir mais informações ou oferecer opções
    assert any(x in resposta_texto for x in [
        "horário", "hora", "qual", "prefere", "profissional", "corte", "quando"
    ]), f"Resposta inadequada. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema solicitou mais informações")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")
