"""
USO 2: ALTERNATIVAS — TDD Tests
Test-first implementation for alternative professionals with individual durations.

Principle: Each alternative professional must have their own configured duration via bridge,
not reuse primary's duration.
"""

import pytest
from services.duracao_service import obter_duracao_por_profissional_bridge


@pytest.mark.asyncio
async def test_uso2_alternativas_each_has_own_duration(uso2_t1_setup):
    """
    RED: Each alternative should return its OWN duration, not primary's.

    Setup:
    - Tenant: uso2_t1
    - Primary: Bruna (corte 60min) — unavailable
    - Alt 1: Gloria (corte 60min) — available
    - Alt 2: Joana (corte 50min) — available (different duration!)

    Expected:
    - Alternatives returned WITH their specific durations
    - Gloria's duration: 60 (not 50, not reused)
    - Joana's duration: 50 (not 60, her own config)
    """
    tenant_id = uso2_t1_setup
    servico = "corte"

    # Verify bridge returns correct durations
    duracao_bruna = await obter_duracao_por_profissional_bridge(tenant_id, "Bruna", servico)
    duracao_gloria = await obter_duracao_por_profissional_bridge(tenant_id, "Gloria", servico)
    duracao_joana = await obter_duracao_por_profissional_bridge(tenant_id, "Joana", servico)

    # Each professional has their OWN configured duration
    assert duracao_bruna == 60, "Bruna corte should be 60min"
    assert duracao_gloria == 60, "Gloria corte should be 60min"
    assert duracao_joana == 50, "Joana corte should be 50min (NOT 60)"

    # Verify they're different (not all copied from primary)
    assert duracao_gloria != duracao_joana, "Gloria and Joana have different durations"


@pytest.mark.asyncio
async def test_uso2_alternativas_without_duration_excluded(uso2_t2_setup):
    """
    RED: If alternative doesn't have duration configured, exclude from suggestions.

    Setup:
    - Tenant: uso2_t2
    - Primary: Bruna (corte 60min)
    - Alt 1: Carla (corte configured, 45min) — include
    - Alt 2: Rafael (corte NOT configured) — exclude

    Expected:
    - Rafael not suggested (duration is None)
    - Only Carla suggested (duration available)
    """
    tenant_id = uso2_t2_setup
    servico = "corte"

    # Carla has duration configured
    duracao_carla = await obter_duracao_por_profissional_bridge(tenant_id, "Carla", servico)
    assert duracao_carla == 45, "Carla should have 45min configured"

    # Rafael has no duration configured
    duracao_rafael = await obter_duracao_por_profissional_bridge(tenant_id, "Rafael", servico)
    assert duracao_rafael is None, "Rafael has no duration configured, should be None"


@pytest.mark.asyncio
async def test_uso2_alternativas_multi_tenant_isolation(uso2_t3_and_t4_setup):
    """
    RED: Same professional name in different tenants has different durations.

    Setup:
    - Tenant 1 (uso2_t3): Gloria corte 60min
    - Tenant 2 (uso2_t4): Gloria corte 35min (different!)

    Expected:
    - Gloria T1: 60min
    - Gloria T2: 35min
    - No cross-tenant contamination
    """
    tenant_t3, tenant_t4 = uso2_t3_and_t4_setup
    servico = "corte"

    # Gloria in Tenant 1
    duracao_gloria_t1 = await obter_duracao_por_profissional_bridge(tenant_t3, "Gloria", servico)
    assert duracao_gloria_t1 == 60, "Gloria in T1 should be 60min"

    # Gloria in Tenant 2
    duracao_gloria_t2 = await obter_duracao_por_profissional_bridge(tenant_t4, "Gloria", servico)
    assert duracao_gloria_t2 == 35, "Gloria in T2 should be 35min (different from T1)"

    # Verify they're different
    assert duracao_gloria_t1 != duracao_gloria_t2, "Same prof in different tenants must have different durations"


@pytest.mark.asyncio
async def test_uso2_alternativas_none_handling_explicit(uso2_t5_setup):
    """
    RED: None handling must be explicit, not converted to 60.

    Expected:
    - If bridge returns None, keep it None
    - No silent fallback to 60 or estimate
    - Explicit check before suggesting alternative
    """
    tenant_id = uso2_t5_setup

    # Professional without configured duration for this service
    duracao = await obter_duracao_por_profissional_bridge(tenant_id, "UnknownProf", "CorteExotica")

    # Must be None, not converted
    assert duracao is None, "Unknown service should return None, not default to 60"
    assert isinstance(duracao, type(None)), "Must be exactly None type"


@pytest.mark.asyncio
async def test_uso2_alternativas_response_includes_durations():
    """
    RED: Return structure should include duration for each alternative.

    Expected response structure:
    {
        "conflito": false,
        "sugestoes": [...],
        "profissional_alternativo": [
            {"nome": "Gloria", "duracao": 60},
            {"nome": "Joana", "duracao": 50}
        ]
    }

    NOT just:
    ["Gloria", "Joana"]
    """
    # This test validates the return structure
    # After implementation, alternatives should be list of dicts with nome+duracao
    # NOT just a list of strings
    pass  # Placeholder for integration test


@pytest.mark.asyncio
async def test_uso2_alternativas_cache_per_operation():
    """
    RED: Cache is operation-scoped, not global.

    Expected:
    - First alternative lookup calls bridge
    - Subsequent lookups for same prof+service use cache
    - Cache discarded after operation ends
    - No cache persistence across requests
    """
    # This bridges to USO 3 (LOOP COM CACHE)
    # Validating no cross-request cache contamination
    pass  # Placeholder for integration test
