"""
Integration examples showing how duracao_service wrapper fits into 4 use cases.

These examples demonstrate usage patterns for:
- USO 1: PRE-CHECK (validate before scheduling)
- USO 2: Alternativa (suggest alternatives)
- USO 3: Loop com cache (batch availability with cache)
- USO 4: Confirmação (confirm details)
"""

import pytest
from services.duracao_service import obter_duracao_por_profissional_nome


# ============================================================================
# USO 1: PRE-CHECK — Validate professional+service before creating event
# ============================================================================
@pytest.mark.asyncio
async def test_uso_1_pre_check_professional_service_validation(monkeypatch):
    """
    Use Case 1 (PRE-CHECK):
    When user requests agendamento, validate BEFORE event creation:
    "Can professional X do service Y, and for how long?"

    Example flow:
    1. User: "Quero agendar corte com a Bruna"
    2. System PRE-CHECK: Is Bruna a profissional? Can she do corte? Duration?
    3. If valid: Proceed to schedule
    4. If invalid: Show error or alternatives
    """
    tenant_id = "customer_123"
    prof_name = "Bruna"
    service = "corte"

    prof_data = {
        "actor_id": "prof_bruna",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {"corte": 60, "escova": 30}
    }

    async def mock_lookup(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_lookup)

    # PRE-CHECK: Get duration for validation
    duracao = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service)

    # Validation logic
    is_valid = duracao is not None
    assert is_valid is True
    assert duracao == 60

    # Use case passes: Professional is valid, service is valid, duration is 60min


# ============================================================================
# USO 2: ALTERNATIVA — Suggest alternative professionals
# ============================================================================
@pytest.mark.asyncio
async def test_uso_2_alternativa_suggest_alternatives(monkeypatch):
    """
    Use Case 2 (ALTERNATIVA):
    Primary professional unavailable → suggest alternatives with same capability.

    Example flow:
    1. User requested: Bruna para corte em 14h
    2. System detects: Bruna busy at that time
    3. System looks for ALTERNATIVES: Which professionals can do corte?
    4. For each candidate, get duration to show options
    """
    tenant_id = "customer_456"
    requested_service = "corte"

    professionals_and_durations = {
        "Bruna": {"duracao": 60, "disponivel": False},      # Primary - busy
        "Gloria": {"duracao": 60, "disponivel": True},      # Alternative 1
        "Joana": {"duracao": 50, "disponivel": True},       # Alternative 2
    }

    # Mock lookup for each professional
    prof_data_map = {
        "Bruna": {
            "actor_id": "prof_bruna", "tenant_id": tenant_id,
            "tipo_usuario": "profissional", "nome": "Bruna", "ativo": True,
            "duracoes": {"corte": 60}
        },
        "Gloria": {
            "actor_id": "prof_gloria", "tenant_id": tenant_id,
            "tipo_usuario": "profissional", "nome": "Gloria", "ativo": True,
            "duracoes": {"corte": 60}
        },
        "Joana": {
            "actor_id": "prof_joana", "tenant_id": tenant_id,
            "tipo_usuario": "profissional", "nome": "Joana", "ativo": True,
            "duracoes": {"corte": 50}
        },
    }

    async def mock_lookup(tid, nome):
        return prof_data_map.get(nome)

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_lookup)

    # ALTERNATIVE LOOKUP: Get options for user
    alternatives = []
    for prof_name, info in professionals_and_durations.items():
        if not info["disponivel"] or prof_name == "Bruna":  # Skip Bruna (primary, busy)
            continue

        duracao = await obter_duracao_por_profissional_nome(tenant_id, prof_name, requested_service)
        if duracao is not None:
            alternatives.append({"profissional": prof_name, "duracao": duracao})

    assert len(alternatives) == 2
    assert alternatives[0] == {"profissional": "Gloria", "duracao": 60}
    assert alternatives[1] == {"profissional": "Joana", "duracao": 50}


# ============================================================================
# USO 3: LOOP COM CACHE — Find available professionals with local cache
# ============================================================================
@pytest.mark.asyncio
async def test_uso_3_loop_cache_batch_availability_check(monkeypatch):
    """
    Use Case 3 (LOOP COM CACHE):
    For multiple services, find professionals who offer ALL of them.
    Use local cache to avoid redundant lookups during same operation.

    Example flow:
    1. User wants multiple services in sequence: escova + hidratação + corte
    2. System needs to find professional who can do ALL three
    3. Within THIS operation, cache professional lookups (don't re-query for each service check)
    4. After operation ends, cache is discarded
    """
    tenant_id = "customer_789"
    services_requested = ["escova", "hidratacao", "corte"]

    prof_data = {
        "actor_id": "prof_bruna_complete",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": "Bruna",
        "ativo": True,
        "duracoes": {
            "escova": 30,
            "hidratacao": 45,
            "corte": 60
        }
    }

    lookup_call_count = {"count": 0}

    async def mock_lookup(tid, nome):
        lookup_call_count["count"] += 1
        if tid == tenant_id and nome == "Bruna":
            return prof_data
        return None

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_lookup)

    # LOOP WITH CACHE: During THIS operation, cache the professional lookup
    prof_cache = {}  # Local cache for this operation only
    prof_name = "Bruna"

    for service in services_requested:
        # Check cache first
        if prof_name not in prof_cache:
            # First time: do the lookup
            duracao = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service)
            # Simulate caching: store the fact that this prof was looked up
            prof_cache[prof_name] = True
        else:
            # Subsequent times: use mock that's already cached
            duracao = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service)

    # Should have called lookup once per service (no smart deduplication expected from wrapper)
    # But the calling code can cache: "prof_cache[prof_name] = prof_data" to avoid re-lookups
    assert lookup_call_count["count"] == 3  # One per service in loop

    # Real optimization would cache the prof_data itself:
    prof_full_cache = {}  # Better cache pattern for this use case

    for service in services_requested:
        if prof_name not in prof_full_cache:
            prof_data_cached = await mock_lookup(tenant_id, prof_name)  # Direct lookup once
            prof_full_cache[prof_name] = prof_data_cached
        # Now check duration in cached prof_data (no need to call wrapper again)

    # After operation: cache is discarded (local scope ends)
    # This ensures cache never spans requests or tenants


# ============================================================================
# USO 4: CONFIRMAÇÃO — Confirm service details with professional data
# ============================================================================
@pytest.mark.asyncio
async def test_uso_4_confirmacao_confirm_booking_details(monkeypatch):
    """
    Use Case 4 (CONFIRMAÇÃO):
    When confirming a booking, retrieve professional data and service details.
    Use this to show user: "Confirmado: Bruna, 14:00–15:00 (corte, 60min)"

    Example flow:
    1. Event created: {profissional: "Bruna", servico: "corte"}
    2. Confirmation step: Get professional's actual configured duration
    3. Validate: Duration on event matches professional's configured duration
    4. Return confirmation message with all details
    """
    tenant_id = "customer_conf"

    # Event data that was created
    event = {
        "id": "evt_123",
        "profissional": "Bruna",
        "servico": "corte",
        "hora_inicio": "14:00",
        "duracao_minutos": 60  # This should match professional's configured duration
    }

    prof_data = {
        "actor_id": "prof_bruna_conf",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": "Bruna",
        "ativo": True,
        "duracoes": {
            "corte": 60,
            "escova": 30
        }
    }

    async def mock_lookup(tid, nome):
        if tid == tenant_id and nome == "Bruna":
            return prof_data
        return None

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_lookup)

    # CONFIRMATION: Get configured duration for the service
    configured_duration = await obter_duracao_por_profissional_nome(
        tenant_id,
        event["profissional"],
        event["servico"]
    )

    # Validate: Event duration matches configured
    is_valid_confirmation = configured_duration == event["duracao_minutos"]
    assert is_valid_confirmation is True

    # Generate confirmation message
    confirmation = {
        "status": "confirmado",
        "profissional": event["profissional"],
        "servico": event["servico"],
        "horario": event["hora_inicio"],
        "duracao": f"{configured_duration}min",
        "mensagem": f"Confirmado: {event['profissional']}, {event['hora_inicio']}–"
                    f"{int(event['hora_inicio'].split(':')[0])+1}:{event['hora_inicio'].split(':')[1]} "
                    f"({event['servico']}, {configured_duration}min)"
    }

    assert confirmation["status"] == "confirmado"
    assert "Bruna" in confirmation["mensagem"]
    assert "60min" in confirmation["mensagem"]
