"""
TESTE DIRECIONADO P0A: Reutilizar identidade.user_id quando identidade existir

Objetivos:
1. Validar que criar_evento usa user_id resolvido no inicio (de identidade)
2. Confirmar que context=None nao causa AttributeError
3. Validar que fallback Telegram continua funcionando
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from utils.identidade_contexto import IdentidadeContexto
from services.gpt_executor import executar_acao_gpt


class TestP0AReutilizarUserID:
    """
    Testes para P0A: Reutilizar identidade.user_id em criar_evento
    """

    @pytest.mark.asyncio
    async def test_cenario_a_whatsapp_com_identidade_valida(self):
        """
        CENARIO A -- WhatsApp: identidade valida, update=None, context=None

        Esperado: user_id e reutilizado de identidade.user_id
        Sem AttributeError ao tentar acessar context.user_data
        """
        # Setup
        identidade_p01 = IdentidadeContexto(
            user_id="5511991382080",
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            canal="whatsapp"
        )

        dados_criar_evento = {
            "profissional": "Carla",
            "servico": "Corte",
            "data_hora": "2026-10-10 14:00",
            "duracao": 30,
            "user_id": "5511991382080",
            "tenant_id": "7394370553",
        }

        with patch("services.gpt_executor.add_evento_por_gpt") as mock_add_evento:
            mock_add_evento.return_value = {
                "ok": True,
                "evento_id": "evt_123",
            }

            # Executar: WhatsApp (update=None, context=None, identidade existe)
            resultado = await executar_acao_gpt(
                update=None,  # WhatsApp: None
                context=None,  # WhatsApp: None
                acao="criar_evento",
                dados=dados_criar_evento,
                identidade=identidade_p01
            )

        # Validacao 1: Funcao foi chamada (significa nao houve AttributeError)
        assert mock_add_evento.called, "add_evento_por_gpt deve ter sido chamado"

        # Validacao 2: user_id correto foi passado
        call_args = mock_add_evento.call_args
        assert call_args is not None
        passed_user_id = call_args[1].get("user_id") or call_args[0][0]
        assert str(passed_user_id) == "5511991382080", f"user_id incorreto: {passed_user_id}"

        print("[OK] CENARIO A PASSOU: WhatsApp com identidade")

    @pytest.mark.asyncio
    async def test_cenario_b_telegram_sem_identidade(self):
        """
        CENARIO B -- Telegram: identidade=None, update/context validos

        Esperado: Continua usando fallback Telegram (update.message.from_user.id)
        """
        # Setup: Telegram Update valido
        mock_user = MagicMock(spec=User)
        mock_user.id = 123456789

        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = 123456789

        mock_message = MagicMock(spec=Message)
        mock_message.from_user = mock_user
        mock_message.chat = mock_chat

        mock_update = MagicMock(spec=Update)
        mock_update.message = mock_message

        mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {}

        dados_criar_evento = {
            "profissional": "Carla",
            "servico": "Corte",
            "data_hora": "2026-10-10 14:00",
            "duracao": 30,
            "user_id": "123456789",
        }

        with patch("services.gpt_executor.add_evento_por_gpt") as mock_add_evento:
            mock_add_evento.return_value = {
                "ok": True,
                "evento_id": "evt_456",
            }

            with patch("services.gpt_executor.obter_id_dono") as mock_obter_dono:
                mock_obter_dono.return_value = "999"

                # Executar: Telegram (update/context validos, identidade=None)
                resultado = await executar_acao_gpt(
                    update=mock_update,  # Telegram: Update valido
                    context=mock_context,  # Telegram: Context valido
                    acao="criar_evento",
                    dados=dados_criar_evento,
                    identidade=None
                )

        # Validacao: Funcao foi chamada com user_id correto
        assert mock_add_evento.called, "add_evento_por_gpt deve ter sido chamado"

        call_args = mock_add_evento.call_args
        assert call_args is not None
        passed_user_id = call_args[1].get("user_id") or call_args[0][0]
        assert str(passed_user_id) == "123456789", f"user_id Telegram incorreto: {passed_user_id}"

        print("[OK] CENARIO B PASSOU: Telegram sem identidade")

    @pytest.mark.asyncio
    async def test_cenario_a_sem_attributeerror(self):
        """
        CENARIO A CRITICO: Garantir que context=None nao causa AttributeError

        Antes da correcao:
            context.user_data -> AttributeError: 'NoneType' object has no attribute 'user_data'

        Depois da correcao:
            user_id reutilizado de identidade.user_id -> sem erro
        """
        identidade_p01 = IdentidadeContexto(
            user_id="5511991382080",
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            canal="whatsapp"
        )

        dados_criar_evento = {
            "profissional": "Carla",
            "servico": "Corte",
            "data_hora": "2026-10-10 14:00",
            "user_id": "5511991382080",
            "tenant_id": "7394370553",
        }

        with patch("services.gpt_executor.add_evento_por_gpt") as mock_add_evento:
            mock_add_evento.return_value = {"ok": True}

            # Teste: Executar SEM excecao
            try:
                resultado = await executar_acao_gpt(
                    update=None,
                    context=None,
                    acao="criar_evento",
                    dados=dados_criar_evento,
                    identidade=identidade_p01
                )
                # Se chegou aqui, sem AttributeError
                print("[OK] Nenhum AttributeError com context=None")

            except AttributeError as e:
                pytest.fail(f"[ERRO] AttributeError nao deveria ocorrer: {e}")

    @pytest.mark.asyncio
    async def test_fallback_dados_se_user_id_falta(self):
        """
        CENARIO A+ -- WhatsApp com fallback para dados

        Se identidade existe mas user_id esta vazio (caso patologico):
        Usar fallback para user_id de dados["user_id"]
        """
        # Setup: identidade com user_id vazio (edge case)
        identidade_vazio = IdentidadeContexto(
            user_id="",
            tenant_id="7394370553",
            actor_id="whatsapp:",
            canal="whatsapp"
        )

        dados_criar_evento = {
            "profissional": "Carla",
            "servico": "Corte",
            "data_hora": "2026-10-10 14:00",
            "user_id": "5511991382080",
            "tenant_id": "7394370553",
        }

        with patch("services.gpt_executor.add_evento_por_gpt") as mock_add_evento:
            mock_add_evento.return_value = {"ok": True}

            resultado = await executar_acao_gpt(
                update=None,
                context=None,
                acao="criar_evento",
                dados=dados_criar_evento,
                identidade=identidade_vazio
            )

        # Validacao: Fallback funcionou
        assert mock_add_evento.called
        call_args = mock_add_evento.call_args
        passed_user_id = call_args[1].get("user_id") or call_args[0][0]
        assert str(passed_user_id) == "5511991382080", "Fallback para dados nao funcionou"

        print("[OK] Fallback de dados funciona corretamente")


class TestP0ARegressao:
    """
    Regressao: Garantir que alteracao nao quebrou outros caminhos
    """

    @pytest.mark.asyncio
    async def test_outra_acao_nao_afetada(self):
        """
        Validar que alteracao em criar_evento nao afetou outras acoes
        """
        identidade = IdentidadeContexto(
            user_id="test_user",
            tenant_id="test_tenant",
            actor_id="whatsapp:test_user",
            canal="whatsapp"
        )

        # Testar outra acao (ex: pre_confirmar_agendamento)
        with patch("services.gpt_executor.pre_confirmar_agendamento") as mock_pre_confirmar:
            mock_pre_confirmar.return_value = {"ok": True}

            resultado = await executar_acao_gpt(
                update=None,
                context=None,
                acao="pre_confirmar_agendamento",
                dados={"data_hora": "2026-10-10 14:00"},
                identidade=identidade
            )

        assert mock_pre_confirmar.called, "Outra acao nao deve ser afetada"
        print("[OK] Outras acoes nao foram afetadas")
