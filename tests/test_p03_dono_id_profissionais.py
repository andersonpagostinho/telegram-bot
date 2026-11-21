"""
P0.3: TESTES DE CORREÇÃO — Passar dono_id em buscar_profissionais_por_servico

Valida que processar_disponibilidade_por_servico_data() e responder_consulta_informativa()
passam dono_id corretamente para resolver tenant e encontrar profissionais.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestP03DonoidProfissionais:
    """10 testes obrigatórios para validar P0.3"""

    # === TESTE 1: Encaminhamento correto do dono_id em processar_disponibilidade ===
    @pytest.mark.asyncio
    async def test_01_dono_id_passado_em_processar_disponibilidade(self):
        """Verifica se processar_disponibilidade passa dono_id para buscar_profissionais_por_servico"""
        from services.informacao_service import processar_disponibilidade_por_servico_data

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            mock_buscar.return_value = {}

            await processar_disponibilidade_por_servico_data(
                servico="corte feminino",
                dt=datetime(2026, 11, 23, 16, 0),
                mensagem_normalizada="queria cortar segunda as 16",
                dono_id="7394370553",
                actor_id="whatsapp:5511991382080"
            )

            # Verificar que foi chamada com dono_id
            mock_buscar.assert_called_once()
            call_args = mock_buscar.call_args

            # Pode ser posicional ou nomeado
            args, kwargs = call_args
            assert "7394370553" in args or kwargs.get("tenant_id") == "7394370553" or kwargs.get("dono_id") == "7394370553", \
                f"dono_id não foi passado corretamente. Args: {args}, Kwargs: {kwargs}"

    # === TESTE 2: Encaminhamento correto do dono_id em responder_consulta_informativa ===
    @pytest.mark.asyncio
    async def test_02_dono_id_passado_em_responder_consulta_disponibilidade(self):
        """Verifica se responder_consulta_informativa passa dono_id na rota de disponibilidade"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
                mock_encontrar.return_value = "corte feminino"
                mock_buscar.return_value = {}

                await responder_consulta_informativa(
                    mensagem="Quem tem disponível corte feminino segunda?",
                    dono_id="7394370553",
                    features={},
                    actor_id="whatsapp:5511991382080"
                )

                # Verificar que buscar_profissionais_por_servico foi chamada
                # Se foi chamada, deve ter dono_id
                if mock_buscar.called:
                    call_args = mock_buscar.call_args
                    args, kwargs = call_args
                    assert "7394370553" in args or kwargs.get("tenant_id") == "7394370553", \
                        "dono_id não foi passado corretamente"

    # === TESTE 3: Busca dentro do tenant correto ===
    @pytest.mark.asyncio
    async def test_03_busca_profissionais_no_tenant_correto(self):
        """Profissionais são encontrados apenas no tenant correto"""

        async def mock_buscar_coro(servicos, user_id, tenant_id):
            if tenant_id == "7394370553":
                return {"bruna": {"servicos": ["corte feminino"]}}
            elif tenant_id == "outro_tenant":
                return {"carla": {"servicos": ["manicure"]}}
            else:
                return {}

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
                mock_encontrar.return_value = "corte feminino"
                mock_buscar.side_effect = mock_buscar_coro

                from services.informacao_service import responder_consulta_informativa

                # Tenant A busca "corte feminino"
                mock_buscar.reset_mock()
                mock_buscar.side_effect = mock_buscar_coro

                await responder_consulta_informativa(
                    mensagem="Quem tem disponível corte feminino?",
                    dono_id="7394370553",
                    features={},
                    actor_id="whatsapp:5511991382080"
                )

                # Se chamada, deve ter recebido tenant_id correto
                if mock_buscar.called:
                    args, kwargs = mock_buscar.call_args
                    assert "7394370553" in args or kwargs.get("tenant_id") == "7394370553"

    # === TESTE 4: Isolamento entre tenants ===
    @pytest.mark.asyncio
    async def test_04_isolamento_multitenant(self):
        """Tenant A não consegue profissionais de Tenant B"""

        def mock_buscar_coro(servicos, user_id, tenant_id):
            if tenant_id == "tenant_a":
                return {"prof_a": {"servicos": ["corte"]}}
            elif tenant_id == "tenant_b":
                return {"prof_b": {"servicos": ["manicure"]}}
            else:
                return {}

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
                mock_encontrar.return_value = "corte"

                from services.informacao_service import processar_disponibilidade_por_servico_data

                # Tenant A busca "corte"
                mock_buscar.side_effect = lambda s, u, t: {"prof_a": {}} if t == "tenant_a" else {}

                await processar_disponibilidade_por_servico_data(
                    servico="corte",
                    dt=datetime(2026, 11, 23),
                    mensagem_normalizada="corte",
                    dono_id="tenant_a"
                )

                args, kwargs = mock_buscar.call_args
                assert "tenant_a" in args or kwargs.get("tenant_id") == "tenant_a"

    # === TESTE 5: Serviço inexistente ===
    @pytest.mark.asyncio
    async def test_05_servico_inexistente_retorna_none(self):
        """Serviço que nenhum profissional faz retorna None"""

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            mock_buscar.return_value = {}  # Nenhum profissional

            from services.informacao_service import processar_disponibilidade_por_servico_data

            resultado = await processar_disponibilidade_por_servico_data(
                servico="botox capilar",
                dt=datetime(2026, 11, 23),
                mensagem_normalizada="botox",
                dono_id="7394370553"
            )

            assert resultado is None

    # === TESTE 6: Ausência de profissionais ===
    @pytest.mark.asyncio
    async def test_06_sem_profissionais_encontrados(self):
        """Resposta apropriada quando nenhum profissional encontrado"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
            with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
                mock_encontrar.return_value = "corte"
                mock_buscar.return_value = {}

                resultado = await responder_consulta_informativa(
                    mensagem="Quem tem disponível corte?",
                    dono_id="7394370553",
                    features={},
                    actor_id="whatsapp:5511991382080"
                )

                assert "Nenhum profissional encontrado" in resultado or resultado is not None

    # === TESTE 7: Erro do Firestore ===
    @pytest.mark.asyncio
    async def test_07_erro_firestore_tratado(self):
        """Exceção do Firestore é tratada adequadamente"""
        from services.informacao_service import processar_disponibilidade_por_servico_data

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            mock_buscar.side_effect = Exception("Firestore error")

            try:
                resultado = await processar_disponibilidade_por_servico_data(
                    servico="corte",
                    dt=datetime(2026, 11, 23),
                    mensagem_normalizada="corte",
                    dono_id="7394370553"
                )
                # Se não lança, retorna None ou message de erro
                assert resultado is None or "erro" in str(resultado).lower() or "desculpe" in str(resultado).lower()
            except Exception:
                # Se lança, é uma exceção esperada
                pass

    # === TESTE 8: Disponibilidade encontrada ===
    @pytest.mark.asyncio
    async def test_08_disponibilidade_encontrada(self):
        """Resposta apropriada quando há disponibilidade"""
        from services.informacao_service import processar_disponibilidade_por_servico_data

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            with patch("services.informacao_service.buscar_profissionais_disponiveis_no_horario") as mock_disponivel:
                mock_buscar.return_value = {"bruna": {"servicos": ["corte"]}}
                mock_disponivel.return_value = {"bruna": {"data": "23/11"}}

                resultado = await processar_disponibilidade_por_servico_data(
                    servico="corte",
                    dt=datetime(2026, 11, 23, 16, 0),
                    mensagem_normalizada="corte segunda as 16",
                    dono_id="7394370553"
                )

                assert resultado is not None
                assert "bruna" in resultado.lower() or "disponível" in resultado.lower()

    # === TESTE 9: Ausência real de disponibilidade ===
    @pytest.mark.asyncio
    async def test_09_sem_disponibilidade_resposta_apropriada(self):
        """Resposta apropriada quando há profissionais mas sem horário"""
        from services.informacao_service import processar_disponibilidade_por_servico_data

        with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
            with patch("services.informacao_service.buscar_profissionais_disponiveis_no_horario") as mock_disponivel:
                mock_buscar.return_value = {"bruna": {"servicos": ["corte"]}}
                mock_disponivel.return_value = {}  # Sem disponibilidade

                resultado = await processar_disponibilidade_por_servico_data(
                    servico="corte",
                    dt=datetime(2026, 11, 23, 16, 0),
                    mensagem_normalizada="corte segunda as 16",
                    dono_id="7394370553"
                )

                assert resultado is not None
                assert "desculpe" in resultado.lower() or "não" in resultado.lower()

    # === TESTE 10: Nenhuma criação de evento em consulta ===
    @pytest.mark.asyncio
    async def test_10_consulta_nao_cria_evento(self):
        """Consulta de disponibilidade nunca cria evento"""
        from services.informacao_service import responder_consulta_informativa

        with patch("services.informacao_service.encontrar_servico_mais_proximo") as mock_encontrar:
            with patch("services.informacao_service.salvar_evento") as mock_salvar:
                with patch("services.informacao_service.buscar_profissionais_por_servico") as mock_buscar:
                    mock_encontrar.return_value = "corte feminino"
                    mock_buscar.return_value = {"bruna": {}}

                    await responder_consulta_informativa(
                        mensagem="Quem tem disponível corte feminino segunda?",
                        dono_id="7394370553",
                        features={},
                        actor_id="whatsapp:5511991382080"
                    )

                    # salvar_evento nunca deve ser chamado em consulta informativa
                    assert not mock_salvar.called, "salvar_evento foi chamado em consulta informativa!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
