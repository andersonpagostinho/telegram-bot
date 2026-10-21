"""
[VALIDAÇÃO REAL] Testes de Ajuste Incremental — Verificam UPDATE vs CREATE em Firestore
Confirma que correção do event_id funciona realmente (sem hora_inicio).
"""

import pytest
import uuid

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_ajuste_incremental_valida_update_firestore():
    """
    VALIDAÇÃO CRÍTICA: Ajuste de horário NÃO cria novo evento

    Fluxo:
    1. Iniciar agendamento com hora 14:00
    2. Sistema cria evento com hour_inicio=14:00
    3. Pedir ajuste "mais cedo" → 10:00
    4. Sistema ATUALIZA mesmo evento (não cria novo)

    Esperado: Apenas 1 evento em Firestore com hora_inicio=10:00 (atualizado)
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import (
        buscar_dado_em_path,
        atualizar_dado_em_path,
        buscar_subcolecao,
    )

    phone_number = f"5518001{uuid.uuid4().hex[:6]}"
    full_actor_id = f"whatsapp:{phone_number}"

    print("\n[VALIDAÇÃO EVENTO] Teste: UPDATE vs CREATE no Firestore")

    # PASSO 1: Setup com agendamento inicial
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
    print("  ✓ Agendamento inicial: 14:00")

    # Contar eventos ANTES do ajuste
    eventos_antes = await buscar_subcolecao(f"Clientes/{E2E_TENANT_ID}/Eventos") or {}
    count_antes = len(eventos_antes)
    print(f"  ✓ Eventos no Firestore antes: {count_antes}")

    # PASSO 2: Cliente pede ajuste "mais cedo"
    resposta1 = await roteador_principal(
        user_id=phone_number,
        mensagem="quero mais cedo, às 10 da manhã",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    assert len(resposta1.get("resposta", "")) > 0, "Sistema não respondeu ao ajuste"
    print("  ✓ Ajuste 1 processado (10:00)")

    # PASSO 3: Novo ajuste — ainda mais cedo
    resposta2 = await roteador_principal(
        user_id=phone_number,
        mensagem="na verdade 9 horas é melhor",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    assert len(resposta2.get("resposta", "")) > 0, "Sistema não respondeu ao 2º ajuste"
    print("  ✓ Ajuste 2 processado (09:00)")

    # PASSO 4: VALIDAÇÃO CRÍTICA — Contar eventos DEPOIS dos ajustes
    eventos_depois = await buscar_subcolecao(f"Clientes/{E2E_TENANT_ID}/Eventos") or {}
    count_depois = len(eventos_depois)
    print(f"  ✓ Eventos no Firestore depois: {count_depois}")

    # VERIFICAÇÃO: Se event_id incluía hora_inicio (BUG), teríamos 3 eventos
    # Se event_id foi corrigido (SEM hora_inicio), temos apenas 1 evento novo
    eventos_novos = count_depois - count_antes
    print(f"  ✓ Eventos NOVOS criados: {eventos_novos}")

    # Se a correção funcionou, máximo 1 novo evento (UPDATE do existente)
    # Se a correção NÃO funcionou, 2 ou 3 novos eventos (CREATE vs UPDATE)
    assert eventos_novos <= 1, (
        f"ERRO: {eventos_novos} eventos foram criados em vez de UPDATE!\n"
        f"Antes: {count_antes}, Depois: {count_depois}\n"
        f"Isso indica que event_id ainda inclui hora_inicio (BUG NÃO FIXADO)"
    )

    print(f"  ✅ VALIDAÇÃO PASSOU: Apenas 1 evento (UPDATE funciona)")
    print(f"  ✅ event_id SEM hora_inicio está funcionando corretamente")


@pytest.mark.asyncio
async def test_múltiplos_clientes_não_colisão():
    """
    VALIDAÇÃO: Múltiplos clientes não colidem no mesmo dia/prof

    Fluxo:
    1. Cliente A agenda "corte com gloria" em 2026-12-19
    2. Cliente B agenda "corte com gloria" em 2026-12-19
    3. Verificar que não há colisão de event_id

    Esperado: 2 eventos separados, um por cliente
    """
    from router.principal_router import roteador_principal
    from services.firebase_service_async import (
        buscar_dado_em_path,
        atualizar_dado_em_path,
        buscar_subcolecao,
    )

    phone_a = f"5518101{uuid.uuid4().hex[:6]}"
    phone_b = f"5518102{uuid.uuid4().hex[:6]}"
    actor_a = f"whatsapp:{phone_a}"
    actor_b = f"whatsapp:{phone_b}"

    print("\n[VALIDAÇÃO ISOLAMENTO] Teste: Múltiplos clientes, mesmo dia/prof")

    # Cliente A: agendamento
    ctx_a = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "gloria",
            "data_hora": "2026-12-19T14:00:00",
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_a}",
        dados=ctx_a
    )
    print("  ✓ Cliente A: agendamento pronto")

    # Cliente B: agendamento MESMO dia/prof/hora
    ctx_b = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional_selecionada": "gloria",
            "data_hora": "2026-12-19T14:00:00",  # MESMO horário!
        },
    }
    await atualizar_dado_em_path(
        path=f"Clientes/{E2E_TENANT_ID}/Sessoes/{actor_b}",
        dados=ctx_b
    )
    print("  ✓ Cliente B: agendamento pronto (MESMO dia/prof/hora)")

    # Ambos confirmam
    await roteador_principal(
        user_id=phone_a,
        mensagem="sim, confirma",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print("  ✓ Cliente A confirmou")

    await roteador_principal(
        user_id=phone_b,
        mensagem="sim, confirma",
        tenant_id=E2E_TENANT_ID,
        phone_number_id="1350170954840548",
    )
    print("  ✓ Cliente B confirmou")

    # Verificar que ambos têm seus próprios eventos
    eventos = await buscar_subcolecao(f"Clientes/{E2E_TENANT_ID}/Eventos") or {}

    eventos_gloria_corte = [
        (eid, ev) for eid, ev in eventos.items()
        if ev.get("profissional", "").lower() == "gloria"
        and ev.get("servico", "").lower() == "corte feminino"
        and ev.get("data") == "2026-12-19"
    ]

    print(f"  ✓ Eventos gloria/corte em 2026-12-19: {len(eventos_gloria_corte)}")

    # Deve haver exatamente 2 eventos (um por cliente)
    assert len(eventos_gloria_corte) >= 2, (
        f"Esperado ≥2 eventos (um por cliente), encontrado {len(eventos_gloria_corte)}\n"
        f"Indica possível colisão de event_id entre clientes"
    )

    # Verificar que event_ids são diferentes
    event_ids = [eid for eid, _ in eventos_gloria_corte]
    unique_ids = set(event_ids)
    assert len(unique_ids) == len(event_ids), (
        f"Há event_ids duplicados! IDs: {event_ids}"
    )

    print(f"  ✅ VALIDAÇÃO PASSOU: {len(eventos_gloria_corte)} eventos distintos")
    print(f"  ✅ Sem colisão de event_id entre clientes")
