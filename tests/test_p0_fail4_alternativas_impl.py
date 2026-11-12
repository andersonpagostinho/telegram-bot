"""
FAIL #4 — ALTERNATIVAS MULTISSERVIÇO — Teste de Integração

Validar que alternativas recebem múltiplos serviços e calculam duração total.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_alternativa_calcula_bloco_completo():
    """
    Alternativa deve calcular duração para bloco completo (manicure + pedicure).

    Esperado:
    - Bruna não está disponível
    - Gloria é alternativa
    - Gloria oferece manicure (30min) + pedicure (35min) = 65min
    - Gloria deve ser sugerida com duração_total=65, não 30

    Status: RED (será GREEN após implementação)
    """
    # Mock da função
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    # Simulação
    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id="tenant1",
        data="2026-11-13",
        hora_inicio="14:00",
        duracao_min=65,  # Manicure + Pedicure
        profissional="Bruna",
        servico="manicure",  # Primary service (backwards compat)
        servicos_bloco=["manicure", "pedicure"]  # Full block
    )

    # Validação
    assert "profissional_alternativo" in resultado
    # TODO: verificar que Gloria é alternativa com duração 65


@pytest.mark.asyncio
async def test_alternativa_sem_servico_rejeitada():
    """
    Alternativa que não oferece um dos serviços deve ser rejeitada.
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id="tenant1",
        data="2026-11-13",
        hora_inicio="14:00",
        duracao_min=65,
        profissional="Bruna",
        servico="manicure",
        servicos_bloco=["manicure", "escova"]  # Se alternativa não oferece escova, rejeitar
    )

    # TODO: Validar que alternativa é rejeitada


@pytest.mark.asyncio
async def test_regressao_servico_unico():
    """
    Serviço único continua funcionando sem servicos_bloco.
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id="tenant1",
        data="2026-11-13",
        hora_inicio="14:00",
        duracao_min=30,  # Apenas manicure
        profissional="Bruna",
        servico="manicure"
        # sem servicos_bloco
    )

    # Deve executar sem erro
    assert isinstance(resultado, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
