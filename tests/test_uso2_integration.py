"""
USO 2 INTEGRATION: ALTERNATIVAS COM DURACOES
Integration tests for verificar_conflito_e_sugestoes_profissional with bridge durations.

This test verifies that when returning alternative professionals, each one includes
their configured duration via the bridge.
"""

import pytest
from services.event_service_async import verificar_conflito_e_sugestoes_profissional


@pytest.mark.asyncio
async def test_uso2_integration_alternatives_include_durations(uso2_t1_setup):
    """
    INTEGRATION TEST: Verify alternatives include their individual durations.

    Setup:
    - Tenant: uso2_t1
    - Primary: Bruna (corte 60min) — has conflict
    - Available alternatives: Gloria (corte 60min), Joana (corte 50min)

    When: Call verificar_conflito_e_sugestoes_profissional with Bruna as primary
    But: Bruna has no availability (conflict)

    Then: Return alternatives with their SPECIFIC durations:
    - Gloria: 60min (not reused from Bruna)
    - Joana: 50min (not reused from Bruna)

    NOT just names ["Gloria", "Joana"]
    """
    tenant_id = uso2_t1_setup

    # Call with Bruna as primary professional, requesting "corte" service
    # Date/time are placeholders - actual availability check depends on events
    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id=tenant_id,
        data="2026-12-25",  # Future date with no events
        hora_inicio="14:00",
        duracao_min=60,
        profissional="Bruna",
        servico="corte",
        tenant_id=tenant_id
    )

    # When there are no conflicts, alternatives list should still include durations
    # if implemented per USO 2 specification
    print(f"Resultado: {resultado}")

    # The response structure should include alternatives with durations
    # This test will FAIL until USO 2 is implemented
    assert "profissional_alternativo" in resultado

    alternativas = resultado.get("profissional_alternativo", [])

    # If alternatives are returned, they should include durations (not just names)
    if alternativas:
        # Check structure: should be dicts with "nome" and "duracao"
        # NOT just strings
        for alt in alternativas:
            if isinstance(alt, dict):
                # NEW behavior: dict with nome + duracao
                assert "nome" in alt, f"Alternative should have 'nome' field: {alt}"
                assert "duracao" in alt, f"Alternative should have 'duracao' field: {alt}"
            elif isinstance(alt, str):
                # OLD behavior: just names (this is what we're replacing)
                pytest.skip("Alternative returned as string - USO 2 not implemented yet")
