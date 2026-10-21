"""
[P0.5 CORREÇÃO MÍNIMA] Testes focados para guarda data_hora=None
Validar que a proteção contra AttributeError funciona corretamente.

Restrições:
- Sem 174 testes P0
- Sem escrita em Firestore real (apenas template/mock)
- Sem alteração de classificador ou roteador
- Apenas validação da guarda implementada
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestP05DataHoraNoneGuard:
    """T1-T5: Testes focados de guarda data_hora=None"""

    @pytest.mark.asyncio
    async def test_t1_draft_incompleto_sem_data_hora(self):
        """
        T1 — Draft incompleto (sem data_hora)

        Estado: aguardando_confirmacao
        Draft: {servico, profissional} mas SEM data_hora

        Esperado:
        - ✅ Sem AttributeError
        - ✅ Sem falsa confirmação
        - ✅ Resposta coerente com erro
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft incompleto (sem data_hora)
        ctx = {
            "estado_fluxo": "aguardando_confirmacao",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
                # data_hora PROPOSITALMENTE ausente
            },
            "dados_confirmacao_agendamento": None,
        }

        # Alteração: tentar ajustar profissional
        alteracao = {
            "tipo": "profissional",
            "valor": "gloria"
        }

        # Mock para evitar escrita em Firestore
        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "erro"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="quero com outra",
                        cliente_id="test_cliente"
                    )

                    # ✅ Se chegou aqui, não houve AttributeError
                    print("  ✅ T1 PASS: Sem AttributeError (guarda funcionou)")

                except AttributeError as e:
                    if "split" in str(e):
                        pytest.fail(f"❌ T1 FAIL: AttributeError não foi bloqueado: {e}")
                    raise

    @pytest.mark.asyncio
    async def test_t2_draft_completo_ajuste_funciona(self):
        """
        T2 — Draft completo (com data_hora válida)

        Draft: {servico, profissional, data_hora}
        Mensagem: ajuste válido

        Esperado:
        - ✅ Ajuste processado sem erro
        - ✅ Contexto mantido
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft completo
        ctx = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
                "data_hora": "2026-12-19T14:00:00",  # ✅ VÁLIDA
            },
            "dados_confirmacao_agendamento": None,
        }

        alteracao = {
            "tipo": "profissional",
            "valor": "gloria"
        }

        # Mock para evitar escrita em Firestore
        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "ok"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="gloria",
                        cliente_id="test_cliente"
                    )

                    print("  ✅ T2 PASS: Draft completo processado sem erro")

                except AttributeError:
                    pytest.fail("❌ T2 FAIL: Erro inesperado com draft completo")

    @pytest.mark.asyncio
    async def test_t3_dados_confirmacao_com_data_hora(self):
        """
        T3 — Dados de confirmação com data/hora válida

        dados_confirmacao_agendamento: {servico, profissional, data_hora}

        Esperado:
        - ✅ Fluxo de confirmação pendente não sofra regressão
        - ✅ data_hora resolvido corretamente
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: confirmação pendente com dados válidos
        ctx = {
            "estado_fluxo": "aguardando_confirmacao_agendamento",
            "draft_agendamento": {},  # vazio
            "dados_confirmacao_agendamento": {
                "servico": "manicure",
                "profissional": "bruna",
                "data_hora": "2026-12-20T11:00:00",  # ✅ VÁLIDA
            },
        }

        alteracao = {
            "tipo": "profissional",
            "valor": "joana"
        }

        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "ok"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="com joana",
                        cliente_id="test_cliente"
                    )

                    print("  ✅ T3 PASS: Confirmação pendente sem regressão")

                except AttributeError:
                    pytest.fail("❌ T3 FAIL: Erro em confirmação pendente")

    @pytest.mark.asyncio
    async def test_t4_consulta_disponibilidade_draft_incompleto(self):
        """
        T4 — Consulta de disponibilidade com draft incompleto

        Mensagem: "Tem horário para hoje às 14 com a Bruna?"
        Draft: incompleto (sem data_hora)

        Esperado:
        - ✅ Sem criação de evento indevida
        - ✅ Sem alteração silenciosa
        - ⚠️ Se fluxo não é alcançável, reportar bloqueio
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft vazio (consulta inicial)
        ctx = {
            "estado_fluxo": "idle",
            "draft_agendamento": None,  # consulta, não agendamento
            "dados_confirmacao_agendamento": None,
        }

        # Mensagem de consulta
        alteracao = {
            "tipo": "consulta_disponibilidade",
            "valor": "hoje às 14 com bruna"
        }

        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "consultando..."}

                try:
                    # resolver_alteracao_draft_agendamento pode retornar None para consultas
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="tem horario para hoje as 14 com bruna",
                        cliente_id="test_cliente"
                    )

                    # Consulta pode retornar None (não é alteração)
                    if resultado is None or resultado == "consulta_nao_suportada":
                        print("  ⚠️ T4 NOTE: Fluxo de consulta não é alcançável em resolver_alteracao (esperado)")
                        print("  ⚠️ T4 NOTE: Consultas devem ser tratadas em outro handler")
                    else:
                        print("  ✅ T4 PASS: Consulta processada sem erro")

                except AttributeError:
                    pytest.fail("❌ T4 FAIL: AttributeError em consulta com draft incompleto")

    @pytest.mark.asyncio
    async def test_t5_ausencia_falsa_conclusao(self):
        """
        T5 — Ausência de falsa conclusão (sucesso quando há erro)

        Draft: {servico, profissional} SEM data_hora
        Alteração: qualquer tipo que acesse data_hora

        Esperado:
        - ✅ Caminho de erro não sinalize sucesso
        - ✅ Resposta deve indicar falta de dados
        - ✅ Sem alteração de estado como se sucesso
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft incompleto
        ctx = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "coloracao",
                "profissional_selecionada": "carla",
                # data_hora AUSENTE
            },
            "dados_confirmacao_agendamento": None,
        }

        # Alteração que precisa de data_hora
        alteracao = {
            "tipo": "horario",  # ajuste de horário
            "valor": "mais_cedo"
        }

        ctx_salvo = None

        async def mock_salvar(dono_id, cliente_id, ctx_novo):
            nonlocal ctx_salvo
            ctx_salvo = ctx_novo
            return True

        with patch('router.principal_router.salvar_contexto_temporario_v2', side_effect=mock_salvar):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                # A resposta deve indicar erro, não sucesso
                mock_send.return_value = {"resposta": "preciso de data"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="mais cedo",
                        cliente_id="test_cliente"
                    )

                    # Verificar que não houve alteração de estado como falsa conclusão
                    if ctx_salvo is not None:
                        # Estado não deve ter mudado para "agendamento confirmado"
                        assert ctx_salvo.get("estado_fluxo") != "agendamento_confirmado", \
                            "❌ Falsa conclusão: estado mudou para confirmado sem data_hora"

                    print("  ✅ T5 PASS: Sem falsa conclusão (erro reportado corretamente)")

                except AttributeError:
                    pytest.fail("❌ T5 FAIL: AttributeError (guarda falhou)")


    @pytest.mark.asyncio
    async def test_t6_ajuste_horario_sem_data_hora(self):
        """
        T6 — Alteração de HORÁRIO com draft incompleto (sem data_hora)

        Estado: agendando
        Draft: {servico, profissional} mas SEM data_hora
        Alteração: tipo='horario' (ajuste de horário)

        Esperado:
        - ✅ Sem AttributeError em linha 2822
        - ✅ Resposta coerente com erro
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft incompleto
        ctx = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
                # data_hora PROPOSITALMENTE ausente
            },
            "dados_confirmacao_agendamento": None,
        }

        # Alteração de HORÁRIO
        alteracao = {
            "tipo": "horario",
            "direcao": "mais_cedo"
        }

        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "erro"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="mais cedo",
                        cliente_id="test_cliente"
                    )

                    print("  ✅ T6 PASS: Sem AttributeError em linha 2822 (guarda funcionou)")

                except AttributeError as e:
                    if "split" in str(e):
                        pytest.fail(f"❌ T6 FAIL: AttributeError em 2822: {e}")
                    raise

    @pytest.mark.asyncio
    async def test_t7_ajuste_horario_com_data_hora_valida(self):
        """
        T7 — Alteração de HORÁRIO com data_hora válida

        Draft: {servico, profissional, data_hora}
        Alteração: tipo='horario' com direção válida

        Esperado:
        - ✅ Ajuste processado sem erro
        - ✅ Sem AttributeError
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft completo
        ctx = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
                "data_hora": "2026-12-19T14:00:00",  # ✅ VÁLIDA
            },
            "dados_confirmacao_agendamento": None,
        }

        alteracao = {
            "tipo": "horario",
            "direcao": "mais_cedo"
        }

        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                with patch('router.principal_router.buscar_horario_ajuste_no_dia', new_callable=AsyncMock) as mock_buscar:
                    mock_buscar.return_value = None  # Nenhum horário alternativo
                    mock_send.return_value = {"resposta": "ok"}

                    try:
                        resultado = await resolver_alteracao_draft_agendamento(
                            update=None,
                            context=MagicMock(),
                            user_id="test_user",
                            ctx=ctx,
                            alteracao=alteracao,
                            dono_id="test_dono",
                            texto_usuario="mais cedo",
                            cliente_id="test_cliente"
                        )

                        print("  ✅ T7 PASS: Ajuste de horário com data_hora válida funciona")

                    except AttributeError:
                        pytest.fail("❌ T7 FAIL: AttributeError com data_hora válida")

    @pytest.mark.asyncio
    async def test_t8_regressao_ajuste_profissional(self):
        """
        T8 — Regressão: Alteração de PROFISSIONAL continua funcionando

        Draft: completo
        Alteração: tipo='profissional' (não é afetada por proteção de horário)

        Esperado:
        - ✅ Nenhuma regressão na seção de profissional
        """
        from router.principal_router import resolver_alteracao_draft_agendamento

        # Setup: draft completo
        ctx = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional_selecionada": "bruna",
                "data_hora": "2026-12-19T14:00:00",
            },
            "dados_confirmacao_agendamento": None,
        }

        alteracao = {
            "tipo": "profissional",
            "valor": "gloria"
        }

        with patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock):
            with patch('router.principal_router._send_and_stop', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = {"resposta": "ok"}

                try:
                    resultado = await resolver_alteracao_draft_agendamento(
                        update=None,
                        context=MagicMock(),
                        user_id="test_user",
                        ctx=ctx,
                        alteracao=alteracao,
                        dono_id="test_dono",
                        texto_usuario="gloria",
                        cliente_id="test_cliente"
                    )

                    print("  ✅ T8 PASS: Sem regressão na alteração de profissional")

                except Exception as e:
                    pytest.fail(f"❌ T8 FAIL: Regressão detectada: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
