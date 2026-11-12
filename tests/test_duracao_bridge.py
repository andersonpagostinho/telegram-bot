"""
Bridge tests: Conectando Atores (identidade) + Profissionais (operações).

Valida:
- Resolução de identidade em Atores
- Localização de config em Profissionais
- Isolamento multi-tenant
- Rejeição de matches ambíguas
- Tratamento de None explícito
"""

import pytest
from services.duracao_service import obter_duracao_por_profissional_bridge


@pytest.mark.asyncio
async def test_bridge_happy_path(monkeypatch):
    """
    Bridge happy path: Ator found, config found, same tenant, duration extracted.
    """
    tenant_id = "bridge_tenant_1"
    prof_name = "Bruna"
    service = "corte"
    expected_duration = 60

    ator_data = {
        "actor_id": "prof_bruna_id",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name,
        "ativo": True
    }

    prof_config = {
        "nome": prof_name,
        "servicos": ["corte", "escova"],
        "duracoes": {
            "corte": expected_duration,
            "escova": 30
        }
    }

    async def mock_buscar_ator(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return ator_data
        return None

    async def mock_buscar_profissionais(path):
        if path == f"Clientes/{tenant_id}/Profissionais":
            return {prof_name: prof_config}
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result = await obter_duracao_por_profissional_bridge(tenant_id, prof_name, service)

    assert result == expected_duration


@pytest.mark.asyncio
async def test_bridge_ator_not_found(monkeypatch):
    """
    Bridge: Ator not found in Atores. Returns None (identity required).
    """
    tenant_id = "bridge_tenant_missing_ator"
    prof_name = "Unknown"
    service = "corte"

    async def mock_buscar_ator(tid, nome):
        return None

    async def mock_buscar_profissionais(path):
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result = await obter_duracao_por_profissional_bridge(tenant_id, prof_name, service)

    assert result is None


@pytest.mark.asyncio
async def test_bridge_config_not_found(monkeypatch):
    """
    Bridge: Ator found but config not in Profissionais. Returns None.
    """
    tenant_id = "bridge_tenant_missing_config"
    prof_name = "Joana"
    service = "corte"

    ator_data = {
        "actor_id": "joana_id",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name
    }

    async def mock_buscar_ator(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return ator_data
        return None

    async def mock_buscar_profissionais(path):
        return {}  # No profissionais config

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result = await obter_duracao_por_profissional_bridge(tenant_id, prof_name, service)

    assert result is None


@pytest.mark.asyncio
async def test_bridge_tenant_isolation(monkeypatch):
    """
    Bridge: Same professional name in different tenants.
    Each tenant returns its own duration, proving isolation.
    """
    prof_name = "Gloria"
    service = "escova"

    ator_t1 = {
        "actor_id": "gloria_t1",
        "tenant_id": "tenant_1",
        "tipo_usuario": "profissional",
        "nome": prof_name
    }

    prof_t1 = {
        "nome": prof_name,
        "duracoes": {"escova": 35}
    }

    ator_t2 = {
        "actor_id": "gloria_t2",
        "tenant_id": "tenant_2",
        "tipo_usuario": "profissional",
        "nome": prof_name
    }

    prof_t2 = {
        "nome": prof_name,
        "duracoes": {"escova": 25}
    }

    async def mock_buscar_ator(tid, nome):
        if tid == "tenant_1" and nome == prof_name:
            return ator_t1
        elif tid == "tenant_2" and nome == prof_name:
            return ator_t2
        return None

    async def mock_buscar_profissionais(path):
        if path == "Clientes/tenant_1/Profissionais":
            return {prof_name: prof_t1}
        elif path == "Clientes/tenant_2/Profissionais":
            return {prof_name: prof_t2}
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result_t1 = await obter_duracao_por_profissional_bridge("tenant_1", prof_name, service)
    result_t2 = await obter_duracao_por_profissional_bridge("tenant_2", prof_name, service)

    assert result_t1 == 35
    assert result_t2 == 25
    assert result_t1 != result_t2  # Confirmed isolation


@pytest.mark.asyncio
async def test_bridge_ambiguous_name_rejected(monkeypatch):
    """
    Bridge: Multiple profissionais with same normalized name (ambiguous).
    Must return None, not pick arbitrarily.
    """
    tenant_id = "bridge_ambig_tenant"
    prof_name = "Maria"
    service = "corte"

    ator_data = {
        "actor_id": "maria_id",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name
    }

    # Two profissionais that normalize to same value
    profissionais_ambig = {
        "Maria": {"nome": "Maria", "duracoes": {"corte": 60}},
        "MARIA": {"nome": "MARIA", "duracoes": {"corte": 75}},
    }

    async def mock_buscar_ator(tid, nome):
        if tid == tenant_id and nome == prof_name:
            return ator_data
        return None

    async def mock_buscar_profissionais(path):
        if path == f"Clientes/{tenant_id}/Profissionais":
            return profissionais_ambig
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result = await obter_duracao_por_profissional_bridge(tenant_id, prof_name, service)

    # Must reject ambiguous (not pick arbitrarily)
    assert result is None


@pytest.mark.asyncio
async def test_bridge_case_insensitive_matching(monkeypatch):
    """
    Bridge: Professional name matching is case-insensitive with unidecode.
    """
    tenant_id = "bridge_case_tenant"
    prof_name_query = "Carla"
    service = "manicure"

    ator_data = {
        "actor_id": "carla_id",
        "tenant_id": tenant_id,
        "tipo_usuario": "profissional",
        "nome": prof_name_query
    }

    prof_config = {
        "nome": "CARLA",  # Stored uppercase
        "duracoes": {"manicure": 30}
    }

    async def mock_buscar_ator(tid, nome):
        if tid == tenant_id and nome == prof_name_query:
            return ator_data
        return None

    async def mock_buscar_profissionais(path):
        if path == f"Clientes/{tenant_id}/Profissionais":
            return {"CARLA": prof_config}
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    result = await obter_duracao_por_profissional_bridge(tenant_id, prof_name_query, service)

    assert result == 30


@pytest.mark.asyncio
async def test_bridge_missing_tenant_id_raises(monkeypatch):
    """
    Bridge: Missing tenant_id raises ValueError (explicit requirement).
    """
    async def mock_buscar_ator(tid, nome):
        return None

    async def mock_buscar_profissionais(path):
        return {}

    monkeypatch.setattr("services.duracao_service.buscar_profissional_por_nome", mock_buscar_ator)
    monkeypatch.setattr("services.duracao_service.buscar_subcolecao", mock_buscar_profissionais)

    with pytest.raises(ValueError):
        await obter_duracao_por_profissional_bridge("", "Prof", "servico")

    with pytest.raises(ValueError):
        await obter_duracao_por_profissional_bridge(None, "Prof", "servico")
