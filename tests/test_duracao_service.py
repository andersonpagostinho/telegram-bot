"""
Test suite for duracao_service.py wrapper.
Tests the integration of buscar_profissional_por_nome + duration extraction.
"""

import pytest
import asyncio
from datetime import datetime
import pytz
from services.duracao_service import obter_duracao_por_profissional_nome
from services.identidade_service import (
    criar_ator_profissional,
    buscar_profissional_por_nome
)
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from services.firestore_client import get_db


# ============================================================================
# TEST 1: Happy Path - Professional exists, duration found
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_por_profissional_nome_happy_path(monkeypatch):
    """
    Scenario: Professional exists in tenant with service durations configured.
    Expected: Should return the duration for the service.
    """
    tenant_id = "test_tenant_happy_path"
    prof_name = "Bruna"
    service_name = "corte"
    expected_duration = 60

    # Mock professional data
    prof_data = {
        "actor_id": "prof_bruna_123",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {
            "corte": expected_duration,
            "escova": 30,
            "hidratacao": 45
        }
    }

    # Mock the lookup function
    async def mock_buscar_prof(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name)

    # ASSERT
    assert result == expected_duration


# ============================================================================
# TEST 2: Professional not found - should return None
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_profissional_nao_encontrado(monkeypatch):
    """
    Scenario: Professional does not exist in tenant.
    Expected: Should return None (no fallback to 60).
    """
    tenant_id = "test_tenant_not_found"
    prof_name = "Inexistente"
    service_name = "corte"

    # Mock: return None for non-existent professional
    async def mock_buscar_prof(tid, nome):
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name)

    # ASSERT
    assert result is None


# ============================================================================
# TEST 3: Service not in professional's duration map - return None
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_servico_nao_configurado(monkeypatch):
    """
    Scenario: Professional exists but service not in their duration map.
    Expected: Should return None (not fallback to 60).
    """
    tenant_id = "test_tenant_service_missing"
    prof_name = "Carla"
    service_name = "manicure"  # Not in Carla's durations

    prof_data = {
        "actor_id": "prof_carla_456",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {
            "corte": 60,
            "escova": 30
            # manicure not present
        }
    }

    async def mock_buscar_prof(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name)

    # ASSERT
    assert result is None


# ============================================================================
# TEST 4: Tenant isolation - Different tenants don't cross-contaminate
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_tenant_isolation(monkeypatch):
    """
    Scenario: Same professional name in two different tenants.
    Expected: Should only look up in the specified tenant.
    """
    prof_name = "Gloria"
    service_name = "corte"

    tenant_1_data = {
        "actor_id": "prof_gloria_tenant1",
        "tenant_id": "tenant_1",
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {"corte": 90}  # Tenant 1: 90 mins
    }

    tenant_2_data = {
        "actor_id": "prof_gloria_tenant2",
        "tenant_id": "tenant_2",
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {"corte": 60}  # Tenant 2: 60 mins
    }

    async def mock_buscar_prof(tid, nome):
        if tid == "tenant_1" and nome == prof_name:
            return tenant_1_data
        elif tid == "tenant_2" and nome == prof_name:
            return tenant_2_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result_tenant_1 = await obter_duracao_por_profissional_nome("tenant_1", prof_name, service_name)
    result_tenant_2 = await obter_duracao_por_profissional_nome("tenant_2", prof_name, service_name)

    # ASSERT
    assert result_tenant_1 == 90
    assert result_tenant_2 == 60
    assert result_tenant_1 != result_tenant_2  # Verify isolation


# ============================================================================
# TEST 5: Alternative duration keys - duracao_servicos
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_alternative_key_duracao_servicos(monkeypatch):
    """
    Scenario: Professional uses alternative key "duracao_servicos" instead of "duracoes".
    Expected: Should find and return the duration.
    """
    tenant_id = "test_tenant_alt_key"
    prof_name = "Joana"
    service_name = "pedicure"
    expected_duration = 40

    prof_data = {
        "actor_id": "prof_joana_789",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracao_servicos": {  # Alternative key
            "pedicure": expected_duration,
            "manicure": 30
        }
    }

    async def mock_buscar_prof(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name)

    # ASSERT
    assert result == expected_duration


# ============================================================================
# TEST 6: Case-insensitive service name matching
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_case_insensitive_matching(monkeypatch):
    """
    Scenario: Service name requested in different case than stored.
    Expected: Should match case-insensitively and return duration.
    """
    tenant_id = "test_tenant_case"
    prof_name = "Bruna"
    service_name_query = "CORTE"  # Uppercase
    service_name_stored = "corte"  # Lowercase
    expected_duration = 60

    prof_data = {
        "actor_id": "prof_bruna_case",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True,
        "duracoes": {
            service_name_stored: expected_duration
        }
    }

    async def mock_buscar_prof(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name_query)

    # ASSERT
    assert result == expected_duration


# ============================================================================
# TEST 7: Professional data exists but no duration fields - return None
# ============================================================================
@pytest.mark.asyncio
async def test_obter_duracao_no_duration_fields(monkeypatch):
    """
    Scenario: Professional found but has no duration configuration.
    Expected: Should return None (not fallback to 60).
    """
    tenant_id = "test_tenant_no_durations"
    prof_name = "Unknown"
    service_name = "corte"

    prof_data = {
        "actor_id": "prof_unknown",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True
        # No durations/duracao_servicos/duracao_por_servico fields
    }

    async def mock_buscar_prof(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return prof_data
        return None

    monkeypatch.setattr(
        "services.duracao_service.buscar_profissional_por_nome",
        mock_buscar_prof
    )

    # ACT
    result = await obter_duracao_por_profissional_nome(tenant_id, prof_name, service_name)

    # ASSERT
    assert result is None
