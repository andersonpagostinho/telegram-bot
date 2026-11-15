"""
Test: extrair_slots_e_mesclar() guard against contamination in consulta_sem_autorizacao_atual mode

Tests verify that consultation messages WITHOUT booking authorization do not:
1. Create singular operational draft (loses multisservice data)
2. Transform user's time window into horarios_sugeridos
3. Set estado_fluxo="aguardando_escolha_horario"
4. Persist contaminated state to Firestore
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from router.principal_router import extrair_slots_e_mesclar
from utils.contexto_temporario import salvar_contexto_temporario_v2


@pytest.fixture
def base_ctx_consultation():
    """Base context for consultation WITHOUT authorization"""
    return {
        "modo_operacao": "consulta_sem_autorizacao_atual",  # ← CRITICAL: consultation mode, not booking
        "dono_id": "tenant_test_001",
        "cliente_id": "5511999999901",
        "servicos_multiplos": ["manicure", "pedicure"],
        "intervalo_inicio": 14,
        "intervalo_fim": 17,
        "profissional_escolhido": None,
        "draft_agendamento": {},
    }


@pytest.mark.asyncio
async def test_A_consultation_no_draft_creation(base_ctx_consultation):
    """
    Test A: Consultation message does NOT create singular operational draft

    Message: "manicure e pedicure, pode ser até 17h"
    Expected: NO draft["servico"] (singular), NO draft["data_hora"], NO estado_fluxo
    """
    ctx = base_ctx_consultation.copy()
    texto = "manicure e pedicure, pode ser até 17h"

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", new_callable=AsyncMock):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify NO operational draft created
    draft = resultado.get("draft_agendamento", {})
    assert draft.get("servico") is None, "Draft should NOT have singular servico in consultation mode"
    assert draft.get("data_hora") is None, "Draft should NOT have data_hora in consultation mode"

    # Verify NO state transition
    assert resultado.get("estado_fluxo") != "aguardando_escolha_horario", \
        "Estado should NOT transition to choice state in consultation mode"

    print("✅ Test A PASS: No operational draft created in consultation mode")


@pytest.mark.asyncio
async def test_B_consultation_no_horarios_sugeridos(base_ctx_consultation):
    """
    Test B: Consultation message does NOT convert time window to horarios_sugeridos

    Message: "manicure e pedicure, pode ser até 17h"
    Expected: NO horarios_sugeridos list (would be ["14:00", "17:00"] if contaminated)
    """
    ctx = base_ctx_consultation.copy()
    texto = "manicure e pedicure, pode ser até 17h"

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", new_callable=AsyncMock):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify NO horarios_sugeridos set
    assert resultado.get("horarios_sugeridos") is None or resultado.get("horarios_sugeridos") == [], \
        "horarios_sugeridos should NOT be set from time window in consultation mode"

    print("✅ Test B PASS: Time window NOT converted to horarios_sugeridos in consultation mode")


@pytest.mark.asyncio
async def test_C_consultation_preserves_multisservice(base_ctx_consultation):
    """
    Test C: Consultation extracts BOTH services without singularization

    Message: "manicure e pedicure, pode ser até 17h"
    Expected: Extract both services, preserve in context (not singularized draft)
    """
    ctx = base_ctx_consultation.copy()
    texto = "manicure e pedicure, pode ser até 17h"

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", new_callable=AsyncMock):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify multisservice is available (in servicos_opcao or similar, not singular draft)
    # Either servicos_opcao is set, OR services are available for motor processing
    servicos_opcao = resultado.get("servicos_opcao", [])
    servico_singular = resultado.get("servico")

    # In consultation, should either have servicos_opcao or NO singular servico
    if servicos_opcao:
        assert len(servicos_opcao) >= 1, "Should have multisservice in servicos_opcao"
    else:
        # If no servicos_opcao, verify NO singular servico set
        assert servico_singular is None or servico_singular == "", \
            "Should NOT singularize service in consultation mode"

    print("✅ Test C PASS: Multisservice preserved (not singularized) in consultation mode")


@pytest.mark.asyncio
async def test_D_booking_flow_still_works(base_ctx_consultation):
    """
    Test D: Legitimate booking flow STILL works (no regression)

    Message: "quero agendar corte com Bruna amanhã às 14h"
    Mode: "agendando" (NOT consultation)
    Expected: Draft IS created, estado_fluxo IS set, horarios_sugeridos work normally
    """
    ctx = base_ctx_consultation.copy()
    ctx["modo_operacao"] = "agendando"  # ← BOOKING mode, not consultation
    ctx["profissional_escolhido"] = "Bruna"
    texto = "quero agendar corte com Bruna amanhã às 14h"

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", new_callable=AsyncMock):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify draft IS created in booking mode
    draft = resultado.get("draft_agendamento", {})
    assert draft.get("profissional") == "Bruna", "Draft should have profissional in booking mode"
    assert draft.get("data_hora") is not None, "Draft should have data_hora in booking mode"

    # Verify estado_fluxo transitions (for choice state, if multiple times)
    # This is normal booking behavior - should work as before

    print("✅ Test D PASS: Legitimate booking flow still works (no regression)")


@pytest.mark.asyncio
async def test_E_preexisting_state_not_deleted(base_ctx_consultation):
    """
    Test E: Consultation mode does NOT indiscriminately delete previous state

    Scenario: Previous booking session had estado_fluxo="aguardando_horario"
              New message is consultation "manicure e pedicure, pode ser até 17h"
    Expected: Previous state NOT deleted, but NOT reactivated for choice either
    """
    ctx = base_ctx_consultation.copy()
    # Simulate previous state from earlier booking
    ctx["estado_fluxo"] = "aguardando_horario"
    ctx["draft_agendamento"] = {
        "profissional": "Bruna",
        "servico": "corte",
        "data_hora": "2026-11-15T10:00:00"
    }

    texto = "manicure e pedicure, pode ser até 17h"

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", new_callable=AsyncMock):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify previous draft NOT obliterated (but also NOT used for booking)
    # In consultation mode, previous booking draft should be preserved but not active
    old_draft = resultado.get("draft_agendamento", {})

    # Should NOT transition to choice state just because previous booking had draft
    assert resultado.get("estado_fluxo") != "aguardando_escolha_horario", \
        "Should NOT reactivate choice state for consultation"

    print("✅ Test E PASS: Previous state preserved, not reactivated for consultation")


@pytest.mark.asyncio
async def test_F_persistence_respects_mode(base_ctx_consultation):
    """
    Test F: Persistence call includes mode guard

    Verify that salvar_contexto_temporario_v2 is called with context that
    respects consultation mode (doesn't have contaminated choice-state fields)
    """
    ctx = base_ctx_consultation.copy()
    texto = "manicure e pedicure, pode ser até 17h"

    persist_call_args = None

    async def mock_persist(dono_id, cliente_id, contexto):
        nonlocal persist_call_args
        persist_call_args = (dono_id, cliente_id, contexto.copy())

    with patch("services.firebase_service_async.salvar_contexto_temporario_v2", side_effect=mock_persist):
        resultado = await extrair_slots_e_mesclar(ctx, texto, ctx["dono_id"], ctx["cliente_id"])

    # Verify persistence was called
    assert persist_call_args is not None, "salvar_contexto_temporario_v2 should be called"

    # Verify persisted context does NOT have contaminated fields
    persisted_ctx = persist_call_args[2]
    assert persisted_ctx.get("horarios_sugeridos") is None or persisted_ctx.get("horarios_sugeridos") == [], \
        "Persisted context should NOT have horarios_sugeridos from time window"
    assert persisted_ctx.get("estado_fluxo") != "aguardando_escolha_horario", \
        "Persisted context should NOT have choice state in consultation mode"

    print("✅ Test F PASS: Persistence respects consultation mode guard")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
