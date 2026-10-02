# -*- coding: utf-8 -*-
# tests/test_p02_executor_multicanal.py

"""
Testes P0.2: Executor Multicanal (agnóstico de canal)

Validar que gpt_executor.executar_acao_gpt() funciona com:
1. IdentidadeContexto (novo, agnóstico)
2. Telegram Update (compatibilidade)
3. WhatsApp (update=None)

Sem quebrar nenhum dos dois.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from utils.identidade_contexto import (
    criar_identidade_whatsapp,
    criar_identidade_telegram,
)


class TestT1_WhatsAppSemTelegramUpdate:
    """T1: Executar sem Telegram Update (case real WhatsApp)."""

    @pytest.mark.asyncio
    async def test_whatsapp_identidade_nao_error(self):
        """
        Simular: update=None, context=None, identidade válida.
        Não deve gerar AttributeError em update.message.
        """
        # Importar dentro do teste para simular contexto P0.2
        from services.gpt_executor import executar_acao_gpt

        # Criar identidade WhatsApp válida
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        # Mock para ação simples (que não precisa de update)
        # Usar uma ação que não toque em update.message
        with patch('services.gpt_executor.add_task_por_gpt', new_callable=AsyncMock) as mock_task:
            mock_task.return_value = None

            # Executar com identidade, update=None
            resultado = await executar_acao_gpt(
                update=None,
                context=None,
                acao="criar_tarefa",
                dados={"descricao": "Teste WhatsApp"},
                identidade=identidade,
            )

            # Deve executar sem erro
            assert resultado is True
            mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_whatsapp_sem_identidade_sem_update_falha(self):
        """
        Simular: update=None, context=None, identidade=None.
        Deve falhar explicitamente (não silenciosamente).
        """
        from services.gpt_executor import executar_acao_gpt

        # Executar sem identidade e sem update
        resultado = await executar_acao_gpt(
            update=None,
            context=None,
            acao="criar_tarefa",
            dados={"descricao": "Teste"},
            identidade=None,
        )

        # Deve retornar False (falha, não error silencioso)
        assert resultado is False


class TestT2_TelegramCompatibilidade:
    """T2: Executar com Telegram mantém compatibilidade."""

    @pytest.mark.asyncio
    async def test_telegram_update_sem_identidade(self):
        """
        Simular: Telegram Update válido, identidade=None.
        Deve usar fallback de update.
        """
        from services.gpt_executor import executar_acao_gpt

        # Criar mock de Telegram Update
        mock_update = MagicMock()
        mock_update.message.from_user.id = 123456789
        mock_update.message.chat.id = 123456789

        mock_context = MagicMock()

        with patch('services.gpt_executor.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
             patch('services.gpt_executor.add_task_por_gpt', new_callable=AsyncMock) as mock_task:

            mock_dono.return_value = "123"  # tenant_id resolv
            mock_task.return_value = None

            # Executar com update, sem identidade
            resultado = await executar_acao_gpt(
                update=mock_update,
                context=mock_context,
                acao="criar_tarefa",
                dados={"descricao": "Teste Telegram"},
                identidade=None,
            )

            # Deve executar com sucesso (fallback)
            assert resultado is True
            mock_dono.assert_called_once_with("123456789")


class TestT3_IdentidadePreservada:
    """T3: IdentidadeContexto chega ao executor preservado."""

    @pytest.mark.asyncio
    async def test_identidade_preservada_em_execucao(self):
        """
        Verificar que tenant_id, actor_id, canal, user_id chegam ao executor.
        """
        from services.gpt_executor import executar_acao_gpt

        # Criar identidade específica
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        # Capturar logs para verificar
        with patch('services.gpt_executor.add_task_por_gpt', new_callable=AsyncMock) as mock_task:
            mock_task.return_value = None

            with patch('builtins.print') as mock_print:
                resultado = await executar_acao_gpt(
                    update=None,
                    context=None,
                    acao="criar_tarefa",
                    dados={},
                    identidade=identidade,
                )

                # Verificar que os dados chegaram
                assert resultado is True

                # Verificar log de P0.2
                calls = [str(call) for call in mock_print.call_args_list]
                log_p02 = [c for c in calls if "P0.2" in c and "Usando IdentidadeContexto" in c]
                assert len(log_p02) > 0, "Log de IdentidadeContexto não encontrado"


class TestT4_UpdateNoneBlocker:
    """T4: update=None não causa AttributeError."""

    @pytest.mark.asyncio
    async def test_update_none_nao_causa_error(self):
        """
        Verificar especificamente que não há:
        AttributeError: 'NoneType' object has no attribute 'message'
        """
        from services.gpt_executor import executar_acao_gpt

        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        # Tentar executar com update=None (o que causaria erro antes)
        try:
            with patch('services.gpt_executor.add_task_por_gpt', new_callable=AsyncMock) as mock_task:
                mock_task.return_value = None

                resultado = await executar_acao_gpt(
                    update=None,  # Crítico
                    context=None,
                    acao="criar_tarefa",
                    dados={},
                    identidade=identidade,
                )

                # Se chegou aqui, não houve AttributeError
                assert resultado is True

        except AttributeError as e:
            pytest.fail(f"AttributeError levantado: {e}")


class TestT5_AcaoReal_CriarEvento:
    """T5: Ação real (criar_evento) funciona sem update."""

    @pytest.mark.asyncio
    async def test_confirmacao_agendamento_whatsapp(self):
        """
        Simular: confirmacao_agendamento via WhatsApp (update=None).
        """
        from services.gpt_executor import executar_acao_gpt

        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        dados = {
            "profissional": "João",
            "servico": "Corte",
            "data_hora": "2026-10-05T14:00",
        }

        with patch('services.gpt_executor.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
             patch('services.gpt_executor.validar_horario_funcionamento', new_callable=AsyncMock) as mock_valid, \
             patch('services.gpt_executor.estimar_duracao') as mock_dur, \
             patch('services.gpt_executor.add_evento_por_gpt', new_callable=AsyncMock) as mock_evento:

            mock_dono.return_value = "7394370553"
            mock_valid.return_value = {"permitido": True}
            mock_dur.return_value = 60
            mock_evento.return_value = {"evento_id": "evt_123"}

            resultado = await executar_acao_gpt(
                update=None,
                context=None,
                acao="pre_confirmar_agendamento",
                dados=dados,
                identidade=identidade,
            )

            # Deve executar
            assert resultado is True


class TestT6_RegressaoTelegram:
    """T6: Testes Telegram existentes continuam funcionando."""

    @pytest.mark.asyncio
    async def test_telegram_tarefa_compatibilidade(self):
        """
        Simular: fluxo Telegram legado (criar_tarefa com update).
        """
        from services.gpt_executor import executar_acao_gpt

        mock_update = MagicMock()
        mock_update.message.from_user.id = 123456789
        mock_update.message.chat.id = 123456789

        mock_context = MagicMock()

        with patch('services.gpt_executor.obter_id_dono', new_callable=AsyncMock) as mock_dono, \
             patch('services.gpt_executor.add_task_por_gpt', new_callable=AsyncMock) as mock_task:

            mock_dono.return_value = "123"
            mock_task.return_value = None

            resultado = await executar_acao_gpt(
                update=mock_update,
                context=mock_context,
                acao="criar_tarefa",
                dados={"descricao": "Minha tarefa"},
                identidade=None,  # Usar fallback
            )

            assert resultado is True
            mock_task.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
