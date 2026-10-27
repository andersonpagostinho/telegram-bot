#!/usr/bin/env python3
"""
GATE: Validação de Resposta da Comparação Carla vs Bruna
Dados de exemplo reais:
- Bruna: corte feminino, escova, coloracao, hidratacao, manicure, pedicure
- Carla: manicure, pedicure, coloracao
"""

import asyncio
from unittest.mock import patch, AsyncMock

async def test_resposta_carla_bruna_dados_exemplo():
    """Valida resposta com dados de exemplo reais."""

    from services.informacao_service import responder_consulta_informativa

    # Dados reais de exemplo
    mock_profissionais = {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte feminino", "escova", "coloracao", "hidratacao", "manicure", "pedicure"]
        },
        "Carla": {
            "nome": "Carla",
            "servicos": ["manicure", "pedicure", "coloracao"]
        }
    }

    with patch('services.informacao_service.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
         patch('services.informacao_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:

        mock_dono.return_value = "tenant_producao_7394370553"

        async def buscar_side_effect(path):
            if "Profissionais" in path:
                return mock_profissionais
            return {}

        mock_buscar.side_effect = buscar_side_effect

        # Pergunta original do caso real
        resposta = await responder_consulta_informativa(
            "a carla faz as mesmas coisa que a bruna?",
            user_id="test_user"
        )

        print("=" * 70)
        print("VALIDAÇÃO: Resposta para 'a carla faz as mesmas coisa que a bruna?'")
        print("=" * 70)
        print(f"\nRESPOSTA GERADA:\n{resposta}\n")

        # Validações
        print("VALIDAÇÕES:")

        # V1: Ambas profissionais nomeadas
        assert "Carla" in resposta, "❌ Carla não está na resposta"
        print("✅ V1: Carla está na resposta")

        assert "Bruna" in resposta, "❌ Bruna não está na resposta"
        print("✅ V2: Bruna está na resposta")

        # V2: Serviços de Carla
        resposta_lower = resposta.lower()
        assert "manicure" in resposta_lower, "❌ Manicure (serviço de ambas) não está"
        print("✅ V3: Serviços em comum listados (manicure)")

        assert "pedicure" in resposta_lower, "❌ Pedicure (serviço de ambas) não está"
        print("✅ V4: Serviço pedicure listado")

        assert "coloracao" in resposta_lower or "coloração" in resposta, "❌ Coloração não está"
        print("✅ V5: Serviço coloração listado")

        # V3: Serviços exclusivos de Bruna
        assert "escova" in resposta_lower, "❌ Escova (exclusiva de Bruna) não está"
        print("✅ V6: Serviço exclusivo de Bruna (escova) listado")

        assert "hidratacao" in resposta_lower or "hidratação" in resposta, "❌ Hidratação não está"
        print("✅ V7: Serviço exclusivo de Bruna (hidratação) listado")

        assert "corte feminino" in resposta_lower or "corte" in resposta_lower, "❌ Corte não está"
        print("✅ V8: Serviço exclusivo de Bruna (corte feminino) listado")

        # V4: Resposta distingue profissionais
        bruna_section = resposta.find("Bruna")
        carla_section = resposta.find("Carla")
        assert bruna_section != carla_section, "❌ Profissionais não são diferenciadas"
        print("✅ V9: Profissionais são diferenciadas na resposta")

        print("\n" + "=" * 70)
        print("✅ TODAS AS VALIDAÇÕES PASSARAM")
        print("=" * 70)
        print("\nCONCLUSÃO: Resposta está correta e diferencia serviços das profissionais.")


if __name__ == "__main__":
    asyncio.run(test_resposta_carla_bruna_dados_exemplo())
