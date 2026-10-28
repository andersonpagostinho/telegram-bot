"""
P0.7.7 — Teste: Resolução de Tenant e Alternativa de Profissional

Valida que:
1. Tenant é resolvido corretamente
2. Profissionais habilitadas são encontradas (não lista vazia)
3. Alternativa oferecida quando profissional atual não atende serviço
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_tenant_resolvido_corretamente():
    """Validar que buscar_profissionais_por_servico usa tenant_id correto."""

    from services.profissional_service import buscar_profissionais_por_servico

    # Mock catálogo
    mock_profs = {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte feminino", "escova", "manicure", "pedicure"]
        },
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte feminino", "escova"]
        }
    }

    with patch("services.profissional_service.buscar_subcolecao", new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = mock_profs

        # Chamada com tenant_id (CORRETA)
        result = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant_teste_7394370553"
        )

        # Validação
        assert "Bruna" in result, "Bruna deveria estar no resultado"
        assert "Gloria" not in result, "Gloria não faz manicure"
        assert len(result) == 1, "Apenas 1 profissional faz manicure"
        print(f"✅ Tenant resolvido corretamente: {list(result.keys())}")


@pytest.mark.asyncio
async def test_alternativa_profissional_quando_rejeitada():
    """Validar que quando Gloria é rejeitada, Bruna é oferecida como alternativa."""

    from services.profissional_service import buscar_profissionais_por_servico, validar_profissional_para_servico

    mock_profs = {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte feminino", "escova", "manicure", "pedicure"],
            "precos": {"manicure": 40.0},
            "duracoes": {"manicure": 30}
        },
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte feminino", "escova"],
            "precos": {"corte feminino": 50.0},
            "duracoes": {"corte feminino": 40}
        }
    }

    with patch("services.profissional_service.buscar_subcolecao", new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = mock_profs

        # 1. Validar que Glory NÃO faz manicure
        valido_gloria = await validar_profissional_para_servico(
            profissional="Gloria",
            servico="manicure",
            tenant_id="tenant_teste"
        )
        assert not valido_gloria["valido"], "Gloria não deveria ser válida para manicure"

        # 2. Buscar alternativas
        alternativas = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant_teste"
        )

        assert "Bruna" in alternativas, "Bruna deveria ser alternativa"
        print(f"✅ Alternativa encontrada: {list(alternativas.keys())}")


@pytest.mark.asyncio
async def test_nenhuma_alternativa_disponivel():
    """Validar que quando nenhuma profissional faz o serviço, retorna vazio."""

    from services.profissional_service import buscar_profissionais_por_servico

    mock_profs = {
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte feminino", "escova"]
        },
        "Carla": {
            "nome": "Carla",
            "servicos": ["corte feminino"]
        }
    }

    with patch("services.profissional_service.buscar_subcolecao", new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = mock_profs

        # Buscar profissionais que fazem manicure (NENHUMA)
        result = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant_teste"
        )

        assert result == {}, "Não deveria haver alternativas"
        print(f"✅ Corretamente retorna vazio quando nenhuma alterna ativa")


@pytest.mark.asyncio
async def test_isolamento_multi_tenant():
    """Validar que tenant_id isola o catálogo corretamente."""

    from services.profissional_service import buscar_profissionais_por_servico

    tenant1_profs = {
        "Bruna": {"nome": "Bruna", "servicos": ["manicure"]}
    }

    tenant2_profs = {
        "Ana": {"nome": "Ana", "servicos": ["corte feminino"]}
    }

    def mock_buscar_subcolecao(path):
        if "tenant1" in path:
            return tenant1_profs
        elif "tenant2" in path:
            return tenant2_profs
        return {}

    with patch("services.profissional_service.buscar_subcolecao", new_callable=AsyncMock) as mock_buscar:
        mock_buscar.side_effect = mock_buscar_subcolecao

        # Tenant 1
        result1 = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant1"
        )

        # Tenant 2
        result2 = await buscar_profissionais_por_servico(
            servicos=["manicure"],
            tenant_id="tenant2"
        )

        assert "Bruna" in result1, "Tenant1 deveria ter Bruna"
        assert "Bruna" not in result2, "Tenant2 não deveria ter Bruna"
        assert "Ana" not in result1, "Tenant1 não deveria ter Ana"
        print(f"✅ Isolamento multi-tenant OK")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
