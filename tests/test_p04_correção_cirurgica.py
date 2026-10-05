"""
P0.4 — Testes de validação das correções cirúrgicas
Objetivo: Confirmar que update=None não causa AttributeError em dois pontos específicos.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
from handlers.event_handler import add_evento_por_gpt


class TestP04CorrecaoCircurgicaAgendaFechada:
    """Teste P0.4 Ponto 1: Agenda fechada com update=None"""

    async def test_agenda_fechada_com_update_none(self):
        """
        Cenário: Horário não está disponível porque salão fecha antes
        Contexto: update=None (WhatsApp)
        Esperado: Não lança AttributeError, retorna False
        """
        # Arrange
        update = None  # ← WhatsApp não tem update
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.chat_data = {}

        dados = {
            "profissional": "Maria",
            "servico": "Corte",
            "data_hora": "2026-10-05 18:30:00",
            "duracao": 60,
            "cliente_nome": "João"
        }

        # Mock para simular agenda fechada (fim_janela < hora solicitada)
        with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
            with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                "aberto": True,
                "fim": "17:00"  # Salão fecha às 17:00, mas usuário quer 18:30
            }):
                with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                    # Act & Assert: Não deve lançar AttributeError
                    try:
                        resultado = await add_evento_por_gpt(update, context, dados)
                        # Se não houver exceção, teste passou
                        assert resultado == False, "Esperado: False (não agendar)"
                        print("✅ Teste PASSOU: Agenda fechada com update=None")
                    except AttributeError as e:
                        if "'NoneType' object has no attribute 'message'" in str(e):
                            pytest.fail(f"❌ AttributeError: {e}")
                        raise


class TestP04CorrecaoCircurgicaExcecao:
    """Teste P0.4 Ponto 2: Exceção geral com update=None"""

    async def test_excecao_geral_com_update_none(self):
        """
        Cenário: Erro inesperado durante add_evento_por_gpt
        Contexto: update=None (WhatsApp)
        Esperado: Não lança AttributeError, retorna False, registra erro
        """
        # Arrange
        update = None  # ← WhatsApp não tem update
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.chat_data = {}

        dados = {
            "profissional": "Maria",
            "servico": "Corte",
            "data_hora": "2026-10-05 18:30:00",
            "duracao": 60,
            "cliente_nome": "João"
        }

        # Mock para simular erro em salvar_evento
        with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
            with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                "aberto": True,
                "fim": "20:00"
            }):
                with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                    # Simular erro durante verificação de conflito ou salvamento
                    with patch('handlers.event_handler.verificar_conflito_agenda', side_effect=Exception("Erro simulado")):
                        # Act & Assert: Não deve lançar AttributeError
                        try:
                            resultado = await add_evento_por_gpt(update, context, dados)
                            # Se não houver exceção, teste passou
                            assert resultado == False, "Esperado: False (erro tratado)"
                            print("✅ Teste PASSOU: Exceção geral com update=None")
                        except AttributeError as e:
                            if "'NoneType' object has no attribute 'message'" in str(e):
                                pytest.fail(f"❌ AttributeError: {e}")
                            raise


class TestP04RegressaoTelegram:
    """Teste P0.4: Regressão Telegram (reply_text continua sendo executado)"""

    async def test_telegram_reply_text_executado(self):
        """
        Cenário: Agenda fechada com Telegram (update != None)
        Esperado: reply_text é executado normalmente
        """
        # Arrange
        user = MagicMock(spec=User)
        user.id = 123
        chat = MagicMock(spec=Chat)
        chat.id = 123
        message = AsyncMock(spec=Message)
        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.chat_data = {}

        dados = {
            "profissional": "Maria",
            "servico": "Corte",
            "data_hora": "2026-10-05 18:30:00",
            "duracao": 60,
            "cliente_nome": "João"
        }

        # Mock para simular agenda fechada
        with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
            with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                "aberto": True,
                "fim": "17:00"  # Salão fecha às 17:00
            }):
                with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                    # Act
                    resultado = await add_evento_por_gpt(update, context, dados)

                    # Assert: reply_text deve ter sido chamado (porque update != None)
                    assert message.reply_text.called, "reply_text deveria ter sido executado para Telegram"
                    print("✅ Teste PASSOU: Telegram continua funcional")


class TestP04NenhombreTagP04:
    """Teste identificar tags P0.4 no código modificado"""

    def test_tags_p04_presentes(self):
        """Confirmar que modificações foram feitas (tags de audit)"""
        with open('handlers/event_handler.py', 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # Verificar se ambos os pontos foram protegidos com if update:
        count_if_update = conteudo.count('if update:\n                        await update.message.reply_text')
        assert count_if_update >= 2, f"Esperado: pelo menos 2 proteções 'if update:', encontrado: {count_if_update}"
        print(f"✅ Teste PASSOU: {count_if_update} proteções 'if update:' encontradas")


if __name__ == "__main__":
    # Rodar testes
    print("\n" + "="*60)
    print("TESTES P0.4 — CORREÇÃO CIRÚRGICA DOS DOIS reply_text() QUEBRADOS")
    print("="*60)

    # Test 1: Agenda fechada com update=None
    print("\n[T1] Agenda fechada com update=None...")
    asyncio.run(TestP04CorrecaoCircurgicaAgendaFechada().test_agenda_fechada_com_update_none())

    # Test 2: Exceção geral com update=None
    print("\n[T2] Exceção geral com update=None...")
    asyncio.run(TestP04CorrecaoCircurgicaExcecao().test_excecao_geral_com_update_none())

    # Test 3: Regressão Telegram
    print("\n[T3] Regressão Telegram (reply_text continua sendo executado)...")
    asyncio.run(TestP04RegressaoTelegram().test_telegram_reply_text_executado())

    # Test 4: Tags P0.4
    print("\n[T4] Tags P0.4 presentes...")
    TestP04NenhombreTagP04().test_tags_p04_presentes()

    print("\n" + "="*60)
    print("✅ TODOS OS TESTES P0.4 COMPLETADOS")
    print("="*60)
