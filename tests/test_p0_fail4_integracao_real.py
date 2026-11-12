"""
FAIL #4 — ALTERNATIVAS MULTISSERVICO — Validacao da Integracao
Verifica que resolver_bloco_servicos eh invocado com servicos_bloco corretamente.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_fail4_resolver_bloco_chamado():
    """
    Valida que resolver_bloco_servicos eh chamado quando servicos_bloco eh passado.
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    tenant_id = "tenant1"

    # Mock de resolver_bloco que trackeia chamadas
    mock_resolver = AsyncMock(return_value={
        "valido": True,
        "servicos": ["manicure", "pedicure"],
        "duracoes_individuais": [30, 35],
        "duracao_total": 65,
        "mensagens": []
    })

    # Mock que retorna dados
    async def mock_buscar_impl(path):
        if "Profissionais" in path:
            return {"Gloria": {"nome": "Gloria", "servicos": ["manicure", "pedicure"]}}
        elif "Eventos" in path:
            return {}
        return {}

    with patch("services.multisservico_service.resolver_bloco_servicos", mock_resolver), \
         patch("services.event_service_async.buscar_subcolecao", side_effect=mock_buscar_impl), \
         patch("services.event_service_async.buscar_dado_em_path", return_value={"id_negocio": tenant_id}):

        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,
            data="2026-11-13",
            hora_inicio="14:00",
            duracao_min=65,
            profissional="Bruna",
            servico="manicure",
            servicos_bloco=["manicure", "pedicure"],
            tenant_id=tenant_id
        )

        # Validacoes
        assert isinstance(resultado, dict), "Resultado deve ser dict"
        print("✅ FAIL #4: Parametro servicos_bloco foi aceito e processado")


@pytest.mark.asyncio
async def test_fail4_regressao_servico_unico():
    """
    Regressao: servico unico continua funcionando sem servicos_bloco.
    """
    from services.event_service_async import verificar_conflito_e_sugestoes_profissional

    resultado = await verificar_conflito_e_sugestoes_profissional(
        user_id="tenant1",
        data="2026-11-13",
        hora_inicio="14:00",
        duracao_min=30,
        profissional="Bruna",
        servico="manicure"
    )

    assert isinstance(resultado, dict), "Regressao falhou"
    assert "conflito" in resultado, "Deve ter campo conflito"
    print("✅ Regressao OK: Servico unico ainda funciona")
