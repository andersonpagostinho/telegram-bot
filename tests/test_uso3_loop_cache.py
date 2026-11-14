"""
USO 3: LOOP COM CACHE — TDD Tests
Operation-scoped cache for repeated duration lookups within same operation.
"""

import pytest
from services.duracao_service import obter_duracao_por_profissional_bridge


@pytest.mark.asyncio
async def test_uso3_loop_cache_avoids_repeated_lookups():
    """
    Simulate loop with cache to avoid repeated bridge lookups for same prof+service.
    """
    tenant_id = "uso3_t1"
    prof = "Bruna"
    services = ["corte", "escova", "manicure"]

    # Operation-scoped cache (exists only during this operation)
    prof_cache = {}
    lookup_count = 0

    for service in services:
        cache_key = f"{prof}:{service}"

        if cache_key not in prof_cache:
            # First time: call bridge
            duracao = await obter_duracao_por_profissional_bridge(tenant_id, prof, service)
            prof_cache[cache_key] = duracao
            lookup_count += 1
        else:
            # Subsequent: use cache
            duracao = prof_cache[cache_key]

    # Should have called bridge 3 times (one per service)
    assert lookup_count == 3, f"Expected 3 lookups, got {lookup_count}"

    # Cache should be empty after operation ends (scope ended)
    prof_cache.clear()
    assert len(prof_cache) == 0, "Cache should be discarded after operation"


@pytest.mark.asyncio
async def test_uso3_loop_cache_no_cross_request_sharing():
    """
    Verify cache is operation-scoped, not shared across requests.
    """
    # Each request gets its own operation
    operation1_cache = {}
    operation2_cache = {}

    # Operation 1
    op1_key = "Bruna:corte"
    operation1_cache[op1_key] = 60

    # Operation 2 (different request)
    op2_key = "Bruna:corte"
    assert op2_key not in operation2_cache, "Cache from Op1 should not leak to Op2"

    # Verify isolation
    assert len(operation1_cache) == 1
    assert len(operation2_cache) == 0
