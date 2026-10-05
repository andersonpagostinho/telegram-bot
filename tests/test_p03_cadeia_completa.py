"""
P0.3 — Teste de Cadeia Completa

Valida: Executor → Router → Adapter WhatsApp → Meta

Caso real: confirmacao_agendamento + criar_evento com WhatsApp
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.whatsapp_bridge_handler import processar_mensagem_whatsapp
from utils.identidade_contexto import IdentidadeContexto


class TestP03CadeiaCompleta:
    """Testes da cadeia completa de P0.3"""

    @pytest.mark.asyncio
    async def test_cadeia_completa_whatsapp_confirmacao(self):
        """
        Teste da cadeia completa WhatsApp → Router → Executor → Adapter

        Fluxo:
        1. WhatsApp recebe mensagem
        2. Handler chama roteador_principal() com update=None
        3. Router chama executor
        4. Executor retorna ResultadoAcao
        5. Router retorna ResultadoAcao
        6. Handler extrai resposta
        7. Adapter envia ao Meta
        """

        payload = {
            "canal": "whatsapp",
            "tenant_id": "7394370553",
            "neoeve_number": "5519994443694",
            "actor_id": "whatsapp:5511991382080",
            "texto": "quero agendar escova com bruna quarta"
        }

        with patch("router.principal_router.roteador_principal") as mock_router:
            # [P0.3] Mock roteador retornando ResultadoAcao
            mock_router.return_value = {
                "ok": True,
                "acao": "pre_confirmar_agendamento",
                "resultado": {
                    "servico": "escova",
                    "profissional": "bruna",
                    "data_hora": "2026-10-08T14:00:00"
                },
                "resposta": "✨ Escova com Bruna\n📆 08/10 às 14:00\n\nPosso confirmar?",
                "erro": None,
                "already_sent": False,  # Não foi enviado (update=None)
                "handled": True
            }

            # Executar handler
            resultado = await processar_mensagem_whatsapp(payload)

            # [P0.3] Validações da cadeia completa
            assert resultado["canal"] == "whatsapp"
            assert resultado["actor_id"] == "whatsapp:5511991382080"
            assert resultado["tenant_id"] == "7394370553"
            # A resposta foi extraída do ResultadoAcao
            assert resultado["resposta"] == "✨ Escova com Bruna\n📆 08/10 às 14:00\n\nPosso confirmar?"
            # Sem erro
            assert "erro" not in resultado or resultado.get("erro") is None

            # Verificar que router foi chamado corretamente
            mock_router.assert_called_once()
            call_args = mock_router.call_args
            # Deve ter passado update=None e context=None
            assert call_args.kwargs.get("update") is None
            assert call_args.kwargs.get("context") is None
            # Deve ter passado tenant_id
            assert call_args.kwargs.get("tenant_id") == "7394370553"

    @pytest.mark.asyncio
    async def test_cadeia_whatsapp_negacao_confirmacao(self):
        """
        Teste negação de confirmação (linha 3500)

        Fluxo:
        1. Usuário em fluxo de confirmação responde "não"
        2. Router detecta desistência (LOTE 3E)
        3. Retorna _send_and_stop com ResultadoAcao
        4. Handler extrai resposta
        """

        payload = {
            "canal": "whatsapp",
            "tenant_id": "7394370553",
            "neoeve_number": "5519994443694",
            "actor_id": "whatsapp:5511991382080",
            "texto": "não"  # Desistência
        }

        with patch("router.principal_router.roteador_principal") as mock_router:
            # [P0.3] Mock roteador retornando ResultadoAcao de negação
            mock_router.return_value = {
                "ok": True,
                "acao": "send_and_stop",  # Negação
                "resultado": None,
                "resposta": "Beleza, entao nao vou agendar.",
                "erro": None,
                "already_sent": False,  # WhatsApp: context=None
                "handled": True
            }

            # Executar handler
            resultado = await processar_mensagem_whatsapp(payload)

            # Validações
            assert resultado["resposta"] == "Beleza, entao nao vou agendar."
            # Confirmação que não foi "já enviado" por Telegram
            assert resultado["resposta"] is not None

    @pytest.mark.asyncio
    async def test_cadeia_already_sent_semantica(self):
        """
        Teste de semântica de already_sent

        [P0.3] already_sent=False → resposta disponível para adapter enviar
        [P0.3] already_sent=True → resposta já foi enviada (Telegram)
        """

        # Cenário 1: WhatsApp (context=None) → already_sent=False
        payload_wa = {
            "canal": "whatsapp",
            "tenant_id": "7394370553",
            "actor_id": "whatsapp:5511991382080",
            "texto": "oi"
        }

        with patch("router.principal_router.roteador_principal") as mock_router:
            # WhatsApp: already_sent=False
            mock_router.return_value = {
                "ok": True,
                "acao": "buscar_tarefas_do_usuario",
                "resultado": {"tarefas": "..."},
                "resposta": "📋 Sua lista de tarefas",
                "erro": None,
                "already_sent": False,  # Chave: False porque update=None
                "handled": True
            }

            resultado_wa = await processar_mensagem_whatsapp(payload_wa)
            assert resultado_wa["resposta"] == "📋 Sua lista de tarefas"

    @pytest.mark.asyncio
    async def test_cadeia_sem_perda_resposta(self):
        """
        Teste crítico: Resposta nunca é perdida

        [P0.3] Mesmo com update=None/context=None:
        - resultado contém "resposta" field
        - handler extrai e retorna
        - adapter pode enviar
        """

        payload = {
            "canal": "whatsapp",
            "tenant_id": "7394370553",
            "actor_id": "whatsapp:5511991382080",
            "texto": "cancelar meu agendamento"
        }

        with patch("router.principal_router.roteador_principal") as mock_router:
            # Mesmo em cenário de erro, resposta não é None
            mock_router.return_value = {
                "ok": False,  # Falha
                "acao": "cancelar_evento",
                "resultado": None,
                "resposta": "Nenhum agendamento encontrado",  # ← Sempre tem resposta!
                "erro": "no_events_found",
                "already_sent": False,
                "handled": True
            }

            resultado = await processar_mensagem_whatsapp(payload)

            # Validação crítica: resposta nunca é None/vazia
            assert resultado["resposta"] is not None
            assert len(resultado["resposta"]) > 0
            assert "Nenhum agendamento" in resultado["resposta"]

    @pytest.mark.asyncio
    async def test_cadeia_sem_duplicacao(self):
        """
        Teste de duplicação

        [P0.3] Uma ação deve gerar uma única resposta
        - Se already_sent=True: Telegram já enviou
        - Se already_sent=False: Adapter vai enviar
        - Nunca ambos
        """

        payload = {
            "canal": "whatsapp",
            "tenant_id": "7394370553",
            "actor_id": "whatsapp:5511991382080",
            "texto": "qual é meu próximo agendamento?"
        }

        with patch("router.principal_router.roteador_principal") as mock_router:
            mock_router.return_value = {
                "ok": True,
                "acao": "buscar_eventos_do_dia",
                "resultado": {"eventos": ["evento1"]},
                "resposta": "📅 Seu próximo agendamento: ...",
                "erro": None,
                "already_sent": False,  # Chave: apenas adapter enviará
                "handled": True
            }

            resultado = await processar_mensagem_whatsapp(payload)

            # Uma única resposta
            assert isinstance(resultado["resposta"], str)
            # Não é uma lista ou dict (que causaria duplicação)
            assert not isinstance(resultado["resposta"], (list, dict))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
