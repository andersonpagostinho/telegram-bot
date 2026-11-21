"""
P0.2: TESTES DE CORREÇÃO - Importação da Implementação Canônica

Valida que informacao_service.py usa normalizacao_service (versão correta)
com catálogo real do tenant, não fallback com "botox capilar".
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestP02ImportacaoCanonica:
    """10 testes obrigatórios para validar P0.2"""

    # Catálogo real do tenant 7394370553
    CATALOGO_REAL = {
        "corte feminino": 40,
        "manicure": 30,
        "escova": 60,
        "hidratacao": 60,
        "coloracao": 120,
        "pedicure": 30
    }

    # === TESTE 1: Função canônica retorna serviço correto ===
    @pytest.mark.asyncio
    async def test_01_funcao_canonica_corte_para_corte_feminino(self):
        """Função canônica mapeia 'cortar' para 'corte feminino'"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            with patch("services.normalizacao_service.obter_id_dono") as mock_obter:
                # Mock: retorna catálogo real
                async def mock_buscar_coro(*args, **kwargs):
                    return {
                        "bruna": {"servicos": list(self.CATALOGO_REAL.keys())},
                        "carla": {"servicos": ["corte feminino", "coloracao"]},
                    }

                mock_buscar.side_effect = mock_buscar_coro
                mock_obter.return_value = "7394370553"

                resultado = await encontrar_servico_mais_proximo(
                    "queria cortar o cabelo",
                    dono_id="7394370553"
                )

                # Deve retornar "corte feminino", não "escova"
                assert resultado == "corte feminino", f"Esperado 'corte feminino', got '{resultado}'"

    # === TESTE 2: Função canônica rejeita "botox capilar" ===
    @pytest.mark.asyncio
    async def test_02_funcao_canonica_rejeita_botox_capilar(self):
        """Função canônica retorna None para 'botox capilar' (não existe)"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            # Mock: retorna catálogo real SEM "botox capilar"
            async def mock_buscar_coro(*args, **kwargs):
                return {
                    "bruna": {"servicos": list(self.CATALOGO_REAL.keys())},
                }

            mock_buscar.side_effect = mock_buscar_coro

            resultado = await encontrar_servico_mais_proximo(
                "botox capilar",
                dono_id="7394370553"
            )

            assert resultado is None, f"'botox capilar' deve ser rejeitado, got '{resultado}'"

    # === TESTE 3: "manicure" é aceito ===
    @pytest.mark.asyncio
    async def test_03_funcao_canonica_manicure_aceito(self):
        """Função canônica retorna 'manicure' para 'quero manicure'"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            async def mock_buscar_coro(*args, **kwargs):
                return {
                    "bruna": {"servicos": list(self.CATALOGO_REAL.keys())},
                }

            mock_buscar.side_effect = mock_buscar_coro

            resultado = await encontrar_servico_mais_proximo(
                "quero manicure",
                dono_id="7394370553"
            )

            assert resultado == "manicure"

    # === TESTE 4: Palavra isolada "o" é rejeitada ===
    @pytest.mark.asyncio
    async def test_04_funcao_canonica_rejeita_palavra_isolada_o(self):
        """'o' sozinho não pode retornar serviço (seria falso match)"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            async def mock_buscar_coro(*args, **kwargs):
                return {
                    "bruna": {"servicos": list(self.CATALOGO_REAL.keys())},
                }

            mock_buscar.side_effect = mock_buscar_coro

            resultado = await encontrar_servico_mais_proximo(
                "o",
                dono_id="7394370553"
            )

            # "o" é muito genérico, deve retornar None
            assert resultado is None

    # === TESTE 5: Catálogo vazio retorna None ===
    @pytest.mark.asyncio
    async def test_05_catalogo_vazio_retorna_none(self):
        """Com catálogo vazio, qualquer busca retorna None"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            mock_buscar.return_value = {}  # Catálogo vazio

            resultado = await encontrar_servico_mais_proximo(
                "cortar o cabelo",
                dono_id="7394370553"
            )

            assert resultado is None

    # === TESTE 6: Dois tenants isolados não cruzam ===
    @pytest.mark.asyncio
    async def test_06_multitenant_isolamento(self):
        """Tenant A não aceita serviço de Tenant B"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        # Tenant A: só tem "corte masculino"
        # Tenant B: só tem "manicure"

        call_count = [0]

        async def mock_buscar_coro(*args, **kwargs):
            call_count[0] += 1
            if "7394370553" in str(args):  # Tenant A
                return {
                    "prof1": {"servicos": ["corte masculino", "barba"]},
                }
            else:  # Tenant B
                return {
                    "prof2": {"servicos": ["manicure", "pedicure"]},
                }

        with patch("services.normalizacao_service.buscar_subcolecao") as mock_buscar:
            mock_buscar.side_effect = mock_buscar_coro

            # Tenant A tenta buscar "manicure" (que não tem)
            resultado_a = await encontrar_servico_mais_proximo(
                "manicure",
                dono_id="7394370553"
            )

            # Tenant B busca "manicure" (que tem)
            resultado_b = await encontrar_servico_mais_proximo(
                "manicure",
                dono_id="outros"
            )

            assert resultado_a is None, "Tenant A não deve aceitar 'manicure'"
            assert resultado_b == "manicure", "Tenant B deve aceitar 'manicure'"

    # === TESTE 7: informacao_service importa versão correta ===
    @pytest.mark.asyncio
    async def test_07_informacao_service_importa_normalizacao(self):
        """Verificar que informacao_service importa de normalizacao_service"""
        import services.informacao_service as info_service
        import inspect

        # Obter a função importada
        funcao = info_service.encontrar_servico_mais_proximo

        # Verificar assinatura tem dono_id
        sig = inspect.signature(funcao)
        parametros = list(sig.parameters.keys())

        assert "dono_id" in parametros, "encontrar_servico_mais_proximo deve ter parâmetro 'dono_id'"
        assert "user_id" in parametros, "encontrar_servico_mais_proximo deve ter parâmetro 'user_id'"

    # === TESTE 8: H2 chama com dono_id ===
    @pytest.mark.asyncio
    async def test_08_h2_passa_dono_id(self):
        """H2 em responder_consulta_informativa chama com dono_id"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
            with patch("services.informacao_service.buscar_subcolecao") as mock_buscar:
                mock_encontrar.return_value = "corte feminino"
                mock_buscar.return_value = {}  # Catálogo vazio para simplificar

                await responder_consulta_informativa(
                    mensagem="Queria cortar o cabelo segunda às 16",
                    dono_id="7394370553",
                    features={
                        "tem_pedido": True,
                        "tem_tempo": True,
                        "tem_pergunta": True,
                    },
                    actor_id="whatsapp:5511991382080"
                )

                # Verificar se foi chamada COM dono_id
                calls = mock_encontrar.call_args_list
                # Pode haver múltiplas chamadas, mas alguma deve ter dono_id="7394370553"
                dono_id_usado = any(
                    call.kwargs.get("dono_id") == "7394370553" or
                    (len(call.args) > 1 and call.args[1] == "7394370553")
                    for call in calls
                )
                assert dono_id_usado, "H2 deve passar dono_id para encontrar_servico_mais_proximo"

    # === TESTE 9: Validação H2 rejeita serviço inexistente ===
    @pytest.mark.asyncio
    async def test_09_h2_validacao_rejeita_botox(self):
        """Se H2 extrair "botox capilar", validação o rejeita"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
            with patch("services.informacao_service.buscar_subcolecao") as mock_buscar:
                # Função retorna "botox capilar"
                mock_encontrar.return_value = "botox capilar"

                # Catálogo real (sem "botox capilar")
                async def mock_buscar_coro(*args, **kwargs):
                    if "Profissionais" in str(args):
                        return {
                            "bruna": {
                                "servicos": ["corte feminino", "manicure", "escova"]
                            }
                        }
                    return {}

                mock_buscar.side_effect = mock_buscar_coro

                # Chamar H2
                resultado = await responder_consulta_informativa(
                    mensagem="Quero botox capilar segunda",
                    dono_id="7394370553",
                    features={"tem_pedido": True, "tem_tempo": True, "tem_pergunta": True},
                    actor_id="whatsapp:5511991382080"
                )

                # Validação deve rejeitar e retornar None ou resposta sem disponibilidade
                assert resultado is None, "Validação deve rejeitar 'botox capilar'"

    # === TESTE 10: E2E - "cortar segunda às 16" fluxo completo ===
    @pytest.mark.asyncio
    async def test_10_e2e_cortar_segunda_as_16(self):
        """Teste ponta a ponta: mensagem → serviço correto → disponibilidade"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
            with patch("services.informacao_service.buscar_subcolecao") as mock_buscar:
                with patch("services.informacao_service.processar_disponibilidade_por_servico_data") as mock_processo:
                    # Função canônica retorna "corte feminino" (correto!)
                    mock_encontrar.return_value = "corte feminino"

                    # Catálogo tem "corte feminino"
                    async def mock_buscar_coro(*args, **kwargs):
                        if "Profissionais" in str(args):
                            return {
                                "bruna": {
                                    "servicos": ["corte feminino", "manicure"],
                                    "duracoes": {"corte feminino": 40}
                                }
                            }
                        return {}

                    mock_buscar.side_effect = mock_buscar_coro

                    # Disponibilidade encontrada
                    mock_processo.return_value = "Sim, posso te atender segunda com Bruna!"

                    resultado = await responder_consulta_informativa(
                        mensagem="Queria cortar o cabelo segunda às 16?",
                        dono_id="7394370553",
                        features={"tem_pedido": True, "tem_tempo": True, "tem_pergunta": True},
                        actor_id="whatsapp:5511991382080"
                    )

                    # Deve retornar resposta de disponibilidade
                    assert resultado is not None, "Deve retornar resposta de disponibilidade"
                    assert "Bruna" in resultado or "atender" in resultado, "Resposta deve mencionar disponibilidade"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
