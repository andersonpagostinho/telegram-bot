#!/usr/bin/env python3
"""
GATE P0.4 — Testes Direcionados (Sem Firestore)
Validar que os dois pontos corrigidos não quebram mais
"""

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

# Adicionar parent directory ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar a função corrigida
from handlers.event_handler import add_evento_por_gpt


class TestP04Gate:
    """Testes do gate de validação P0.4"""

    async def test_ponto1_agenda_fechada_update_none(self):
        """
        Cenário 1: Agenda fechada com update=None
        Esperado: Não lança AttributeError, retorna False
        """
        print("\n[TESTE 1] Agenda fechada com update=None...")

        # Arrange
        update = None  # ← WhatsApp
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

        try:
            with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
                with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                    "aberto": True,
                    "fim": "17:00"  # Salão fecha às 17:00, horário solicitado: 18:30
                }):
                    with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                        # Act
                        resultado = await add_evento_por_gpt(update, context, dados)

                        # Assert
                        assert resultado == False, "Esperado: False (não agendar)"
                        print("  ✅ PASSOU: Sem AttributeError, retornou False")
                        return True

        except AttributeError as e:
            if "'NoneType' object has no attribute 'message'" in str(e):
                print(f"  ❌ FALHOU: AttributeError ainda presente: {e}")
                return False
            raise
        except Exception as e:
            print(f"  ❌ FALHOU: Exceção inesperada: {e}")
            return False


    async def test_ponto2_excecao_geral_update_none(self):
        """
        Cenário 2: Exceção geral com update=None
        Esperado: Não lanza AttributeError, retorna False
        """
        print("\n[TESTE 2] Exceção geral com update=None...")

        # Arrange
        update = None  # ← WhatsApp
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

        try:
            with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
                with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                    "aberto": True,
                    "fim": "20:00"
                }):
                    with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                        # Simular erro durante processamento
                        with patch('handlers.event_handler.verificar_conflito_agenda', side_effect=Exception("Erro simulado")):
                            # Act
                            resultado = await add_evento_por_gpt(update, context, dados)

                            # Assert
                            assert resultado == False, "Esperado: False (erro tratado)"
                            print("  ✅ PASSOU: Sem AttributeError, retornou False")
                            return True

        except AttributeError as e:
            if "'NoneType' object has no attribute 'message'" in str(e):
                print(f"  ❌ FALHOU: AttributeError ainda presente: {e}")
                return False
            raise
        except Exception as e:
            print(f"  ❌ FALHOU: Exceção inesperada: {e}")
            return False


    async def test_regressao_telegram_agenda_fechada(self):
        """
        Regressão: Agenda fechada com Telegram (update válido)
        Esperado: reply_text continua sendo executado
        """
        print("\n[TESTE 3] Regressão Telegram — Agenda fechada...")

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

        try:
            with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
                with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                    "aberto": True,
                    "fim": "17:00"  # Salão fecha antes da hora solicitada
                }):
                    with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                        # Act
                        resultado = await add_evento_por_gpt(update, context, dados)

                        # Assert
                        assert message.reply_text.called, "reply_text deveria ter sido executado"
                        print("  ✅ PASSOU: Telegram continua executando reply_text()")
                        return True

        except Exception as e:
            print(f"  ❌ FALHOU: {e}")
            return False


    async def test_regressao_telegram_excecao(self):
        """
        Regressão: Exceção com Telegram (update válido)
        Esperado: reply_text de erro continua sendo executado
        """
        print("\n[TESTE 4] Regressão Telegram — Exceção geral...")

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

        try:
            with patch('handlers.event_handler.obter_id_dono', return_value="owner_123"):
                with patch('handlers.event_handler.buscar_expediente_salao', return_value={
                    "aberto": True,
                    "fim": "20:00"
                }):
                    with patch('handlers.event_handler.buscar_eventos_por_intervalo', return_value=[]):
                        # Simular erro
                        with patch('handlers.event_handler.verificar_conflito_agenda', side_effect=Exception("Erro simulado")):
                            # Act
                            resultado = await add_evento_por_gpt(update, context, dados)

                            # Assert
                            assert message.reply_text.called, "reply_text de erro deveria ter sido executado"
                            print("  ✅ PASSOU: Telegram continua executando reply_text() de erro")
                            return True

        except Exception as e:
            print(f"  ❌ FALHOU: {e}")
            return False


async def main():
    """Executar todos os testes"""
    print("\n" + "="*70)
    print("GATE P0.4 — TESTES DIRECIONADOS")
    print("="*70)

    tester = TestP04Gate()

    # Testes WhatsApp (update=None)
    t1 = await tester.test_ponto1_agenda_fechada_update_none()
    t2 = await tester.test_ponto2_excecao_geral_update_none()

    # Testes Telegram (regressão)
    t3 = await tester.test_regressao_telegram_agenda_fechada()
    t4 = await tester.test_regressao_telegram_excecao()

    # Resultado
    print("\n" + "="*70)
    print("RESULTADO DO GATE P0.4")
    print("="*70)

    testes = [
        ("P0.4.1 WhatsApp — Agenda Fechada", t1),
        ("P0.4.2 WhatsApp — Exceção Geral", t2),
        ("P0.4.R1 Telegram — Agenda Fechada", t3),
        ("P0.4.R2 Telegram — Exceção", t4),
    ]

    total_pass = sum(1 for _, r in testes if r)
    total = len(testes)

    for nome, resultado in testes:
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"  {status}: {nome}")

    print(f"\nTotal: {total_pass}/{total} PASS")

    if total_pass == total:
        print("\n✅ GATE P0.4 APROVADO")
        print("="*70)
        return 0
    else:
        print("\n❌ GATE P0.4 BLOQUEADO")
        print("="*70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
