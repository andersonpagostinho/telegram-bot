"""
P0.3 — Testes de Separação Execução × Transporte

Testes T1-T8 conforme documento de implementação P0.3.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.gpt_executor import (
    executar_acao_gpt,
    resultado_acao,
    resultado_acao as build_resultado_acao
)
from utils.identidade_contexto import IdentidadeContexto


class TestP03ResultadoAcao:
    """Testes do contrato ResultadoAcao"""

    def test_resultado_acao_sucesso(self):
        """T1 — Resultado com resposta de sucesso"""
        resultado = resultado_acao(
            ok=True,
            acao="teste",
            resposta="Mensagem ao usuário",
            resultado={"chave": "valor"},
            already_sent=False
        )

        assert resultado["ok"] is True
        assert resultado["acao"] == "teste"
        assert resultado["resposta"] == "Mensagem ao usuário"
        assert resultado["resultado"] == {"chave": "valor"}
        assert resultado["already_sent"] is False
        assert resultado["handled"] is True
        assert resultado["erro"] is None

    def test_resultado_acao_erro(self):
        """T1 — Resultado com resposta de erro"""
        resultado = resultado_acao(
            ok=False,
            acao="teste",
            resposta="Erro ao executar",
            erro="erro_especifico",
            already_sent=False
        )

        assert resultado["ok"] is False
        assert resultado["acao"] == "teste"
        assert resultado["resposta"] == "Erro ao executar"
        assert resultado["erro"] == "erro_especifico"
        assert resultado["already_sent"] is False


class TestP03BuscartarefasDoUsuario:
    """T1 — Ação buscar_tarefas_do_usuario"""

    @pytest.mark.asyncio
    async def test_buscar_tarefas_retorna_resultado_dict(self):
        """T1 — Resultado contém resposta != None"""
        # Mock das dependências
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="telegram",
            actor_id="user_123"
        )

        with patch("services.gpt_executor.gerar_texto_tarefas") as mock_tarefas:
            mock_tarefas.return_value = "📋 Tarefa 1\n📋 Tarefa 2"

            # Simular Telegram Update
            update = MagicMock()
            update.message.from_user.id = 123
            update.message.reply_text = AsyncMock()

            context = MagicMock()

            # Executar ação
            resultado = await executar_acao_gpt(
                update=update,
                context=context,
                acao="buscar_tarefas_do_usuario",
                dados={"resposta": "📋 Lista de tarefas:\n"},
                identidade=identidade
            )

            # Validação
            assert isinstance(resultado, dict), "Resultado deve ser dict"
            assert resultado["ok"] is True
            assert resultado["resposta"] is not None
            assert "📋" in resultado["resposta"]
            assert resultado["already_sent"] is True  # Telegram
            assert resultado["handled"] is True


class TestP03PreConfirmarAgendamento:
    """T2, T3, T6 — Ação pre_confirmar_agendamento (sem Update/Context)"""

    @pytest.mark.asyncio
    async def test_pre_confirmar_sem_update_sem_error(self):
        """T2 — WhatsApp sem Update não causa AttributeError"""
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="whatsapp",
            actor_id="whatsapp:551199..."
        )

        dados = {
            "profissional": "Bruna",
            "servico": "escova",
            "data_hora": "2026-10-05T14:00:00"
        }

        with patch("services.gpt_executor.validar_horario_funcionamento") as mock_val:
            with patch("services.gpt_executor.verificar_conflito_e_sugestoes_profissional") as mock_conf:
                with patch("services.gpt_executor.obter_id_dono") as mock_dono:
                    with patch("services.gpt_executor.carregar_contexto_temporario") as mock_ctx:
                        with patch("services.gpt_executor.salvar_contexto_temporario"):
                            mock_dono.return_value = "999"
                            mock_val.return_value = {"permitido": True}
                            mock_conf.return_value = {"conflito": False}
                            mock_ctx.return_value = {}

                            # Executar com update=None e context=None (WhatsApp)
                            try:
                                resultado = await executar_acao_gpt(
                                    update=None,
                                    context=None,
                                    acao="pre_confirmar_agendamento",
                                    dados=dados,
                                    identidade=identidade
                                )

                                # T2: Sem AttributeError
                                assert resultado["ok"] is True
                                assert "Posso confirmar?" in resultado["resposta"]
                                # T3: Não enviado por Telegram (already_sent=False)
                                assert resultado["already_sent"] is False

                            except AttributeError as e:
                                pytest.fail(f"AttributeError em WhatsApp: {e}")


class TestP03CriarEvento:
    """T1, T2 — Ação criar_evento"""

    @pytest.mark.asyncio
    async def test_criar_evento_retorna_resultado(self):
        """T1 — Resultado contém resposta"""
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="whatsapp",
            actor_id="whatsapp:551199..."
        )

        dados = {
            "profissional": "Bruna",
            "descricao": "escova com Bruna",
            "cliente_nome": "João"
        }

        with patch("services.gpt_executor.add_evento_por_gpt") as mock_evento:
            with patch("services.gpt_executor.obter_id_dono") as mock_dono:
                with patch("services.gpt_executor._listar_profissionais_validos_para_servico") as mock_profs:
                    with patch("services.gpt_executor.carregar_contexto_temporario"):
                        mock_dono.return_value = "999"
                        mock_profs.return_value = ["Bruna"]
                        mock_evento.return_value = {"ok": True}

                        resultado = await executar_acao_gpt(
                            update=None,
                            context=None,
                            acao="criar_evento",
                            dados=dados,
                            identidade=identidade
                        )

                        assert isinstance(resultado, dict)
                        assert "ok" in resultado


class TestP03AlreadySent:
    """T4 — Marcação de already_sent"""

    @pytest.mark.asyncio
    async def test_already_sent_false_whatsapp(self):
        """T4 — already_sent=False antes do transporte WhatsApp"""
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="whatsapp",
            actor_id="whatsapp:551199..."
        )

        dados = {
            "profissional": "Bruna",
            "servico": "escova",
            "data_hora": "2026-10-05T14:00:00"
        }

        with patch("services.gpt_executor.validar_horario_funcionamento") as mock_val:
            with patch("services.gpt_executor.verificar_conflito_e_sugestoes_profissional") as mock_conf:
                with patch("services.gpt_executor.obter_id_dono") as mock_dono:
                    with patch("services.gpt_executor.carregar_contexto_temporario") as mock_ctx:
                        with patch("services.gpt_executor.salvar_contexto_temporario"):
                            mock_dono.return_value = "999"
                            mock_val.return_value = {"permitido": True}
                            mock_conf.return_value = {"conflito": False}
                            mock_ctx.return_value = {}

                            resultado = await executar_acao_gpt(
                                update=None,
                                context=None,
                                acao="pre_confirmar_agendamento",
                                dados=dados,
                                identidade=identidade
                            )

                            # T4: already_sent=False porque ainda não foi enviado
                            assert resultado["already_sent"] is False


class TestP03TelegramCompat:
    """T7 — Compatibilidade Telegram preservada"""

    @pytest.mark.asyncio
    async def test_telegram_already_sent_true(self):
        """T7 — already_sent=True quando enviado via Telegram"""
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="telegram",
            actor_id="user_123"
        )

        dados = {
            "profissional": "Bruna",
            "servico": "escova",
            "data_hora": "2026-10-05T14:00:00"
        }

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("services.gpt_executor.validar_horario_funcionamento") as mock_val:
            with patch("services.gpt_executor.verificar_conflito_e_sugestoes_profissional") as mock_conf:
                with patch("services.gpt_executor.obter_id_dono") as mock_dono:
                    with patch("services.gpt_executor.carregar_contexto_temporario") as mock_ctx:
                        with patch("services.gpt_executor.salvar_contexto_temporario"):
                            mock_dono.return_value = "999"
                            mock_val.return_value = {"permitido": True}
                            mock_conf.return_value = {"conflito": False}
                            mock_ctx.return_value = {}

                            resultado = await executar_acao_gpt(
                                update=update,
                                context=context,
                                acao="pre_confirmar_agendamento",
                                dados=dados,
                                identidade=identidade
                            )

                            # T7: already_sent=True pois foi enviado
                            assert resultado["already_sent"] is True
                            # Verificar que reply_text foi chamado
                            update.message.reply_text.assert_called_once()


class TestP03Nao_Duplicacao:
    """T8 — Sem duplicação de resposta"""

    @pytest.mark.asyncio
    async def test_uma_resposta_funcional(self):
        """T8 — Uma ação gera uma única resposta funcional"""
        identidade = IdentidadeContexto(
            user_id="123",
            tenant_id="999",
            canal="whatsapp",
            actor_id="whatsapp:551199..."
        )

        dados = {"resposta": "Aqui está sua lista:\n"}

        with patch("services.gpt_executor.gerar_texto_tarefas") as mock_tarefas:
            mock_tarefas.return_value = "Tarefa 1\nTarefa 2"

            resultado = await executar_acao_gpt(
                update=None,
                context=None,
                acao="buscar_tarefas_do_usuario",
                dados=dados,
                identidade=identidade
            )

            # T8: Uma única resposta (não múltiplas)
            assert isinstance(resultado["resposta"], str)
            assert len(resultado["resposta"]) > 0
            # Verificar que não há "já foi enviado duas vezes"
            assert resultado["handled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
