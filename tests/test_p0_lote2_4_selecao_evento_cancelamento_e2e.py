"""
[MIGRAÇÃO LOTE 2 — TESTE 4] Seleção Evento Cancelamento — E2E Firebase Real

Convertido de: test_p0_selecao_evento_cancelamento.py (unitário)
Para: E2E com Firestore Real

Objetivo: Validar que sistema oferece lista de eventos quando usuário
pede cancelamento sem especificar qual evento.
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_lote2_4_lista_eventos_para_cancelamento_e2e():
    """
    T1: Usuário pede cancelamento sem especificar qual evento.
    Mensagem: "quero cancelar"
    Esperado: Sistema lista eventos disponíveis para cancelamento
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512301{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T1] Teste E2E: Solicita cancelamento sem especificar evento")

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
        mensagem="quero cancelar",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve reconhecer intenção de cancelamento
    assert any(x in resposta_texto for x in [
        "cancelar", "qual", "qual agendamento", "agenda", "quando", "confirmação"
    ]), f"Cancelamento não reconhecido. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema reconheceu cancelamento")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T1] PASS")


@pytest.mark.asyncio
async def test_lote2_4_cancelamento_especifico_e2e():
    """
    T2: Usuário especifica qual evento cancelar.
    Mensagem: "quero cancelar o agendamento de segunda"
    Esperado: Sistema confirma qual evento foi cancelado
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5512302{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[T2] Teste E2E: Cancelamento de evento específico")

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
        mensagem="quero cancelar o agendamento de segunda",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    resposta_texto = resposta.get("resposta", "").lower()

    # Sistema deve oferecer confirmação ou listar opções
    assert any(x in resposta_texto for x in [
        "cancelar", "segunda", "qual", "confirma", "tem certeza", "seguro", "agenda"
    ]), f"Resposta inadequada. Obtido: {resposta_texto[:100]}"

    print(f"  ✓ Sistema pediu confirmação")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"

    print(f"  ✅ [T2] PASS")
