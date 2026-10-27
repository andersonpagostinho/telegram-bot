#!/usr/bin/env python3
"""
GATE: Validação de Não-Regressão
Testa que handlers anteriores (endereço, serviços, preços) continuam funcionando.
"""

import asyncio
from unittest.mock import patch, AsyncMock

async def test_regressao_handlers():
    """Valida que handlers antigos ainda funcionam."""

    from services.informacao_service import responder_consulta_informativa

    print("=" * 70)
    print("REGRESSÃO: Validando handlers anteriores")
    print("=" * 70)

    # T-R1: Consulta de endereço (continua funcionando)
    print("\n[R1] Testando consulta de endereço...")
    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_endereco_negocio', new_callable=AsyncMock) as mock_endereco:

        mock_dono.return_value = "tenant_test"
        mock_endereco.return_value = {"completo": "Rua das Flores, 123"}

        resposta = await responder_consulta_informativa("Qual é o endereço?", "test_user")

        assert resposta is not None, "❌ Endereço não respondido"
        assert "Rua das Flores" in resposta, "❌ Endereço não contém os dados"
        print("✅ R1: Consulta de endereço continua funcionando")

    # T-R2: Consulta de serviços (continua funcionando)
    print("\n[R2] Testando listagem de serviços...")
    mock_profs = {
        "Prof1": {"servicos": ["corte", "escova"]},
        "Prof2": {"servicos": ["manicure"]}
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profs
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "Que serviços vocês oferecem?",
            "test_user"
        )

        assert resposta is not None, "❌ Serviços não respondidos"
        assert "corte" in resposta.lower() or "Corte" in resposta, "❌ Serviço não listado"
        print("✅ R2: Listagem de serviços continua funcionando")

    # T-R3: Consulta de preços (continua funcionando)
    print("\n[R3] Testando consulta de preços...")
    mock_profs_precos = {
        "Prof1": {
            "precos": {
                "corte": "30",
                "escova": "40"
            }
        }
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_test"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profs_precos
            return {}

        mock_buscar.side_effect = buscar_side_effect

        resposta = await responder_consulta_informativa(
            "Quanto custa um corte?",
            "test_user"
        )

        assert resposta is not None, "❌ Preço não respondido"
        print("✅ R3: Consulta de preços continua funcionando")

    # T-R4: Consulta de disponibilidade (delegada ao fluxo normal, não responde direto)
    print("\n[R4] Testando que disponibilidade NÃO é respondida como comparação...")

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono:
        mock_dono.return_value = "tenant_test"

        resposta = await responder_consulta_informativa(
            "Quem tem disponível amanhã?",
            "test_user"
        )

        # Disponibilidade pode retornar None (delegado) ou uma resposta,
        # mas não deve ser respondida como comparação
        if resposta:
            assert "comparacao" not in resposta.lower(), "❌ Disponibilidade foi respondida como comparação"

        print("✅ R4: Disponibilidade não é respondida como comparação")

    print("\n" + "=" * 70)
    print("✅ SEM REGRESSÕES DETECTADAS")
    print("=" * 70)
    print("Todos os handlers anteriores continuam funcionando corretamente.")


if __name__ == "__main__":
    asyncio.run(test_regressao_handlers())
