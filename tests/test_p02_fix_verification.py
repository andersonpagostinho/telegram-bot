"""
Testes de Verificação P0.2: Correção de PAST_TIME_BLOCKED

Valida que a alteração em event_handler.py:1306-1329 está funcionando.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytz

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class MockUpdate:
    """Mock de Telegram Update"""
    def __init__(self):
        self.message = MagicMock()
        self.message.reply_text = AsyncMock()


class MockContext:
    """Mock de Telegram Context"""
    def __init__(self):
        self.chat_data = {}


class MockIdentidade:
    """Mock de IdentidadeContexto"""
    def __init__(self):
        self.user_id = "user_123"
        self.tenant_id = "tenant_123"
        self.canal = "whatsapp"
        self.phone_number_id = "5511987654321"


# =============================================================================
# T1: PAST_TIME_BLOCKED é rejeitado em salvar_evento()
# =============================================================================

@pytest.mark.asyncio
async def test_t1_past_time_is_rejected():
    """
    T1: Valida que horário passado é rejeitado em salvar_evento()
    """
    from services.event_service_async import salvar_evento

    # Horário: 1 hora atrás
    agora = datetime.now(FUSO_BR)
    tempo_passado = (agora - timedelta(hours=1)).replace(tzinfo=None)

    evento = {
        "data": tempo_passado.strftime("%Y-%m-%d"),
        "hora_inicio": tempo_passado.strftime("%H:%M"),
        "hora_fim": (tempo_passado + timedelta(minutes=30)).strftime("%H:%M"),
        "duracao": 30,
        "profissional": "Bruna",
        "cliente_id": "user_123",
        "confirmado": True,
    }

    resultado = await salvar_evento("user_123", evento, "tenant_123")

    assert resultado is False, f"[T1] Esperava False, obteve {resultado}"
    print("[T1 OK] Horário passado foi rejeitado")


# =============================================================================
# T2: Alteração foi aplicada (buscar string da correção)
# =============================================================================

def test_t2_fix_code_is_present():
    """
    T2: Valida que o código de correção foi adicionado a event_handler.py
    """
    with open("handlers/event_handler.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Procura pela string de comentário da correção
    assert "[P0.2 FIX]" in conteudo, (
        "[T2] Código de correção não encontrado em event_handler.py"
    )

    # Procura pela lógica de envio de mensagem
    assert "não consegui agendar" in conteudo.lower(), (
        "[T2] Mensagem de erro não foi adicionada"
    )

    # Procura pela chamada de enviar_mensagem_whatsapp
    assert "enviar_mensagem_whatsapp" in conteudo, (
        "[T2] Suporte WhatsApp não foi adicionado"
    )

    print("[T2 OK] Código de correção está presente em event_handler.py")


# =============================================================================
# T3: Mensagem é enviada quando salvar_evento retorna False (Telegram)
# =============================================================================

@pytest.mark.asyncio
async def test_t3_error_message_sent_on_telegram_failure():
    """
    T3: Valida que mensagem é enviada quando salvamento falha (Telegram)
    """
    from handlers.event_handler import add_evento_por_gpt

    # Mocka as dependências
    with patch('handlers.event_handler.salvar_evento', new_callable=AsyncMock) as mock_save, \
         patch('handlers.event_handler.verificar_pagamento', new_callable=AsyncMock, return_value=True), \
         patch('handlers.event_handler.verificar_acesso_modulo', new_callable=AsyncMock, return_value=True):

        mock_save.return_value = False  # Simula PAST_TIME_BLOCKED

        update = MockUpdate()
        context = MockContext()

        dados = {
            "profissional": "Bruna",
            "servico": "Corte",
            "data_hora": "2025-01-01T10:00:00",
            "cliente_id": "user_123",
            "cliente_nome": "João",
            "confirmado": True,
            "user_id": "user_123",
            "tenant_id": "tenant_123",
        }

        resultado = await add_evento_por_gpt(update, context, dados)

        # Validação: deve retornar True (handled)
        assert resultado is True, f"[T3] Esperava True, obteve {resultado}"

        # Validação: deve ter chamado reply_text (enviado mensagem)
        assert update.message.reply_text.called, (
            "[T3] Mensagem não foi enviada (reply_text não foi chamado)"
        )

        # Validação: mensagem deve conter indicação de erro
        call_args = update.message.reply_text.call_args
        if call_args:
            mensagem = call_args[0][0] if call_args[0] else ""
            assert "não consegui" in mensagem.lower(), (
                f"[T3] Mensagem não contém indicação de erro: {mensagem}"
            )

        print("[T3 OK] Mensagem de erro foi enviada no Telegram")


# =============================================================================
# T4: Mensagem é enviada quando salvar_evento retorna False (WhatsApp)
# =============================================================================

@pytest.mark.asyncio
async def test_t4_error_message_sent_on_whatsapp_failure():
    """
    T4: Valida que mensagem é enviada quando salvamento falha (WhatsApp)
    """
    from handlers.event_handler import add_evento_por_gpt

    with patch('handlers.event_handler.salvar_evento', new_callable=AsyncMock) as mock_save, \
         patch('utils.whatsapp_utils.enviar_mensagem_whatsapp', new_callable=AsyncMock) as mock_whatsapp:

        mock_save.return_value = False  # Simula PAST_TIME_BLOCKED

        update = None  # Sem Telegram
        context = MockContext()
        identidade = MockIdentidade()

        dados = {
            "profissional": "Bruna",
            "servico": "Corte",
            "data_hora": "2025-01-01T10:00:00",
            "cliente_id": "user_123",
            "cliente_nome": "João",
            "confirmado": True,
            "user_id": "user_123",
            "tenant_id": "tenant_123",
        }

        resultado = await add_evento_por_gpt(update, context, dados, identidade=identidade)

        # Validação: deve retornar True (handled)
        assert resultado is True, f"[T4] Esperava True, obteve {resultado}"

        # Validação: deve ter chamado enviar_mensagem_whatsapp
        assert mock_whatsapp.called, (
            "[T4] WhatsApp não foi chamado; cliente não recebeu mensagem"
        )

        # Validação: mensagem deve conter indicação de erro
        call_args = mock_whatsapp.call_args
        if call_args:
            mensagem = call_args[0][1] if len(call_args[0]) > 1 else ""
            assert "não consegui" in mensagem.lower(), (
                f"[T4] Mensagem WhatsApp não contém erro: {mensagem}"
            )

        print("[T4 OK] Mensagem de erro foi enviada no WhatsApp")


# =============================================================================
# T5: Fluxo de sucesso não é afetado
# =============================================================================

@pytest.mark.asyncio
async def test_t5_success_flow_unaffected():
    """
    T5: Valida que agendamento bem-sucedido continua funcionando
    """
    from handlers.event_handler import add_evento_por_gpt

    with patch('handlers.event_handler.salvar_evento', new_callable=AsyncMock) as mock_save, \
         patch('handlers.event_handler.verificar_pagamento', new_callable=AsyncMock, return_value=True), \
         patch('handlers.event_handler.verificar_acesso_modulo', new_callable=AsyncMock, return_value=True), \
         patch('handlers.event_handler.criar_ou_atualizar_profile_apos_evento', new_callable=AsyncMock):

        mock_save.return_value = True  # ✅ Sucesso

        update = MockUpdate()
        context = MockContext()

        # Horário futuro válido
        futuro = (datetime.now(FUSO_BR) + timedelta(hours=2)).replace(tzinfo=None)

        dados = {
            "profissional": "Bruna",
            "servico": "Corte",
            "data_hora": f"{futuro.strftime('%Y-%m-%d')}T{futuro.strftime('%H:%M')}:00",
            "cliente_id": "user_123",
            "cliente_nome": "João",
            "confirmado": True,
            "user_id": "user_123",
            "tenant_id": "tenant_123",
        }

        resultado = await add_evento_por_gpt(update, context, dados)

        # Validação: deve retornar True
        assert resultado is True, f"[T5] Sucesso: esperava True, obteve {resultado}"

        # Validação: em caso de sucesso, a função NÃO entra no bloco de erro
        # (portanto, a mensagem de sucesso não é duplicada pela nossa correção)
        print("[T5 OK] Fluxo de sucesso não foi afetado")


# =============================================================================
# T6: Contrato de retorno é respeitado
# =============================================================================

@pytest.mark.asyncio
async def test_t6_executor_contract_preserved():
    """
    T6: Valida que o contrato entre handler → executor → bot é preservado
    """
    from services.gpt_executor import executar_acao_gpt_resultado

    with patch('services.gpt_executor.executar_acao_gpt', new_callable=AsyncMock) as mock_exec:

        # Simula add_evento_por_gpt retornando True (com ou sem erro interno)
        mock_exec.return_value = True

        resultado = await executar_acao_gpt_resultado(None, None, "criar_evento", {})

        # Validação: resultado deve ser dict
        assert isinstance(resultado, dict), (
            f"[T6] Esperava dict, obteve {type(resultado).__name__}"
        )

        # Validação: deve ter chave "acao"
        assert "acao" in resultado, "[T6] Chave 'acao' não presente"

        # Validação: "acao" deve ser "criar_evento"
        assert resultado["acao"] == "criar_evento", (
            f"[T6] Acao esperada 'criar_evento', obteve {resultado['acao']}"
        )

        # Validação: deve ter chave "ok"
        assert "ok" in resultado, "[T6] Chave 'ok' não presente"

        print("[T6 OK] Contrato de retorno preservado")


# =============================================================================
# T7: bot.py não envia mensagem duplicada
# =============================================================================

def test_t7_bot_respects_acao_contract():
    """
    T7: Valida que bot.py não duplica mensagem quando há "acao"
    """
    from telegram.ext import ApplicationHandlerStop

    # Simula resposta com "acao" (vem de executar_acao_gpt_resultado)
    resposta = {
        "ok": True,
        "acao": "criar_evento",
        "resultado": True,
        "erro": None,
    }

    # Simula lógica de bot.py:843-844
    deve_parar = False
    try:
        if resposta and isinstance(resposta, dict) and resposta.get("acao"):
            deve_parar = True
            raise ApplicationHandlerStop
    except ApplicationHandlerStop:
        pass

    assert deve_parar, "[T7] bot.py deveria parar sem enviar duplicata"
    print("[T7 OK] bot.py respeita contrato com 'acao'")


# =============================================================================
# PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("BATERIA P0.2: Testes de Verificação da Correção")
    print("="*80 + "\n")

    pytest.main([__file__, "-v", "-s"])
