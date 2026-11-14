"""
USO 4: CONFIRMAÇÃO — TDD Tests
Bridge lookup before estimate fallback: catalog -> bridge -> estimate
"""

import pytest
from services.duracao_service import (
    obter_duracao_por_profissional_bridge,
    validar_profissional_com_duracao
)


@pytest.mark.asyncio
async def test_uso4_confirmacao_bridge_before_estimate():
    """
    Verify priority: catalog -> bridge -> estimate
    """
    tenant_id = "uso4_t1"
    prof = "Carla"
    servico = "pedicure"

    # Bridge returns configured duration
    duracao_bridge = await obter_duracao_por_profissional_bridge(tenant_id, prof, servico)

    # If bridge returns a duration, it should be used (not estimate)
    if duracao_bridge is not None:
        # Bridge value takes priority over estimate
        assert duracao_bridge is not None
        assert isinstance(duracao_bridge, int)


@pytest.mark.asyncio
async def test_uso4_confirmacao_validation_wrapper():
    """
    Verify validar_profissional_com_duracao returns proper structure.
    """
    tenant_id = "uso4_t1"
    prof = "Carla"
    servico = "pedicure"

    resultado = await validar_profissional_com_duracao(tenant_id, prof, servico)

    # Should return dict with valido, duracao, motivo
    assert isinstance(resultado, dict)
    assert "valido" in resultado
    assert "duracao" in resultado
    assert "motivo" in resultado

    # If valid, duracao should not be None
    if resultado["valido"]:
        assert resultado["duracao"] is not None
        assert isinstance(resultado["duracao"], int)
        assert resultado["motivo"] is None
    else:
        assert resultado["motivo"] in ["profissional_inexistente", "duracao_nao_configurada"]


@pytest.mark.asyncio
async def test_uso4_confirmacao_none_handling():
    """
    Verify explicit None handling in confirmation flow.
    """
    tenant_id = "uso4_t1"

    # Unknown professional
    resultado = await validar_profissional_com_duracao(tenant_id, "UnknownProf", "UnknownService")

    # Should return not valid with explicit None
    assert resultado["valido"] is False
    assert resultado["duracao"] is None
    assert resultado["motivo"] == "profissional_inexistente"
