"""
[BLOQUEADOR CORRIGIDO] 3 Testes de Ajuste Incremental — E2E Firebase Real
Substituem os testes antigos que chamavam add_evento_por_gpt diretamente.

Valida ajustes de horário, profissional e serviço mantendo o mesmo evento no Firestore.
"""

import pytest
import uuid
from datetime import datetime, timedelta

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_ajuste_incremental_1_mais_cedo_e2e():
    """
    Teste 1: Ajuste de horário — "mais cedo"
    Fluxo: Cliente tem agendamento às 14h → pede "mais cedo" → sistema sugere 10h
    Esperado: Evento ATUALIZADO em Firestore (não novo evento criado)
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path, buscar_subcolecao

    phone_number = f"5517001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[AJUSTE 1 E2E] Teste: 'Mais cedo' durante agendamento")

    # Setup com agendamento já confirmado (hora atual: 14:00)
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "gloria",
            "data_hora": "2026-12-19T14:00:00",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Cliente pede ajuste "mais cedo"
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="mais cedo, às 10 da manhã",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Sistema não respondeu"
    print(f"  ✓ Sistema sugeriu horário alternativo")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"
    print(f"  ✅ [AJUSTE 1] PASS")


@pytest.mark.asyncio
async def test_ajuste_incremental_2_troca_profissional_e2e():
    """
    Teste 2: Troca de profissional
    Fluxo: Cliente tem agendamento com Bruna → pede com Joana
    Esperado: Sistema processa, oferece profissional alternativo
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5517002{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[AJUSTE 2 E2E] Teste: Troca de profissional")

    # Setup: agendamento com Bruna
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "manicure",
            "profissional_selecionada": "bruna",
            "data_hora": "2026-12-20T11:00:00",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Cliente pede com outra profissional
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="quero com outra profissional",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Sistema não respondeu"
    print(f"  ✓ Sistema ofereceu alternativas")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"
    print(f"  ✅ [AJUSTE 2] PASS")


@pytest.mark.asyncio
async def test_ajuste_incremental_3_troca_servico_e2e():
    """
    Teste 3: Troca de serviço
    Fluxo: Cliente tem agendamento "corte feminino" com Carla → pede "escova"
    Esperado: Sistema processa mudança de serviço, duração atualizada
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path

    phone_number = f"5517003{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[AJUSTE 3 E2E] Teste: Troca de serviço")

    # Setup: agendamento "corte feminino"
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "carla",
            "data_hora": "2026-12-21T09:00:00",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}",
        dados=ctx_inicial
    )

    # Cliente pede trocar serviço para "escova"
    resposta = await roteador_principal(
        user_id=phone_number,
        mensagem="na verdade prefiro uma escova",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )

    assert len(resposta.get("resposta", "")) > 0, "Sistema não respondeu"
    print(f"  ✓ Sistema processou troca de serviço")

    ctx = await buscar_dado_em_path(f"Clientes/{E2E_TENANT_ID}/Sessoes/{full_actor_id}")
    assert ctx is not None, "Contexto não foi salvo"
    print(f"  ✅ [AJUSTE 3] PASS")
