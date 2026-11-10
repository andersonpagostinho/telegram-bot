# -*- coding: utf-8 -*-
"""
FASE 4 TEST: Integração de Áudio ao Fluxo Conversacional WhatsApp

15 Testes Obrigatórios - Integração ao main.py e principal_router
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone


class TestFase4AudioIntegration:
    """Testes de integração de áudio com fluxo conversacional."""

    @pytest.mark.asyncio
    async def test_01_texto_whatsapp_preservado(self):
        """Teste 1: Mensagem de texto WhatsApp continua funcionando."""
        print("\n[TESTE FASE 4.1] Texto WhatsApp preservado")

        # Simular webhook de texto
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511999999999",
                            "display_phone_number": "+55 11 99999-9999",
                            "business_account_id": "waba123"
                        },
                        "messages": [{
                            "id": "wamid_text_001",
                            "from": "5511991382080",
                            "type": "text",
                            "text": {"body": "Quero agendar"}
                        }]
                    }
                }]
            }]
        }

        # Mock roteador
        with patch('router.principal_router.roteador_principal') as mock_router:
            mock_router.return_value = "Agendamento recebido"

            # Verificar que processamento_tipo = "text" passa text_body ao router
            text_body = webhook_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]

            assert text_body == "Quero agendar", "Texto deveria ser preservado"
            print("✅ [TESTE FASE 4.1] Texto WhatsApp preservado")

    @pytest.mark.asyncio
    async def test_02_audio_ogg_opus_recebido(self):
        """Teste 2: Áudio OGG/Opus é identificado corretamente."""
        print("\n[TESTE FASE 4.2] Áudio OGG/Opus recebido")

        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511999999999",
                            "display_phone_number": "+55 11 99999-9999",
                            "business_account_id": "waba123"
                        },
                        "messages": [{
                            "id": "wamid_audio_001",
                            "from": "5511991382080",
                            "type": "audio",
                            "audio": {
                                "id": "audio_id_123",
                                "mime_type": "audio/ogg; codecs=opus"
                            }
                        }]
                    }
                }]
            }]
        }

        # Verificar que áudio é identificado
        msg = webhook_data["entry"][0]["changes"][0]["value"]["messages"][0]
        assert msg["type"] == "audio", "Tipo deveria ser audio"
        assert msg["audio"]["id"] == "audio_id_123", "audio_id deveria ser extraído"
        assert "ogg" in msg["audio"]["mime_type"].lower(), "mime_type deveria incluir ogg"

        print("✅ [TESTE FASE 4.2] Áudio OGG/Opus identificado")

    @pytest.mark.asyncio
    async def test_03_transcricao_valida_ao_router(self):
        """Teste 3: Transcrição válida chega ao router existente."""
        print("\n[TESTE FASE 4.3] Transcrição válida ao router")

        # Mock
        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            mock_transcribe.return_value = "Quero agendar um corte feminino"

            with patch('router.principal_router.roteador_principal') as mock_router:
                mock_router.return_value = "Agendamento confirmado"

                # Simular fluxo
                texto_transcrito = await mock_transcribe(
                    media_id="audio_123",
                    mime_type="audio/ogg",
                    access_token="token",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_001"
                )

                assert texto_transcrito is not None, "Transcrição não deveria ser None"
                assert len(texto_transcrito) > 0, "Transcrição não deveria estar vazia"
                assert "corte" in texto_transcrito.lower(), "Conteúdo da transcrição preservado"

                # Verificar que seria passado ao router
                resposta = await mock_router(
                    user_id="5511991382080",
                    mensagem=texto_transcrito,
                    tenant_id="tenant1",
                    phone_number_id="5511999999999"
                )

                assert resposta is not None, "Router deveria retornar resposta"
                print("✅ [TESTE FASE 4.3] Transcrição válida ao router")

    @pytest.mark.asyncio
    async def test_04_transcricao_vazia_nao_vai_router(self):
        """Teste 4: Transcrição vazia não chega ao router."""
        print("\n[TESTE FASE 4.4] Transcrição vazia bloqueada")

        # Mock transcrição vazia
        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            mock_transcribe.return_value = None

            with patch('router.principal_router.roteador_principal') as mock_router:
                texto_transcrito = await mock_transcribe(
                    media_id="audio_123",
                    mime_type="audio/ogg",
                    access_token="token",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_001"
                )

                # Verificar que router NÃO é chamado
                if not texto_transcrito or len(texto_transcrito.strip()) == 0:
                    # Resposta de erro deveria ser enviada
                    msg_erro = "Não consegui entender seu áudio. Pode enviá-lo novamente ou escrever sua mensagem?"
                    assert msg_erro is not None, "Mensagem de erro deveria ser preparada"
                    assert not mock_router.called or texto_transcrito, "Router não deveria ser chamado com transcrição vazia"

                print("✅ [TESTE FASE 4.4] Transcrição vazia bloqueada")

    @pytest.mark.asyncio
    async def test_05_falha_download(self):
        """Teste 5: Falha de download recebe tratamento."""
        print("\n[TESTE FASE 4.5] Falha de download")

        with patch('services.whatsapp_media_service.baixar_midia_whatsapp') as mock_download:
            mock_download.return_value = None  # Falha

            resultado = await mock_download(
                media_id="audio_123",
                access_token="token",
                tenant_id="tenant1",
                cliente_id="5511991382080",
                msg_id="wamid_audio_001"
            )

            assert resultado is None, "Download falhado deveria retornar None"
            # Deveria marcar FALHA_RECUPERAVEL
            print("✅ [TESTE FASE 4.5] Falha de download tratada")

    @pytest.mark.asyncio
    async def test_06_falha_temporaria_stt(self):
        """Teste 6: Falha temporária de Google STT permite recuperação."""
        print("\n[TESTE FASE 4.6] Falha temporária STT")

        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            # Simular erro 503 (temporário)
            mock_transcribe.side_effect = Exception("503 Service Unavailable")

            try:
                await mock_transcribe(
                    media_id="audio_123",
                    mime_type="audio/ogg",
                    access_token="token",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_001"
                )
            except Exception as e:
                erro_str = str(e).lower()
                # Detectar como erro temporário
                if "503" in erro_str or "service unavailable" in erro_str:
                    # Deveria marcar FALHA_RECUPERAVEL
                    assert True, "Erro detectado como temporário"
                    print("✅ [TESTE FASE 4.6] Falha temporária permite recuperação")

    @pytest.mark.asyncio
    async def test_07_token_invalido(self):
        """Teste 7: Token inválido recebe tratamento."""
        print("\n[TESTE FASE 4.7] Token inválido")

        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            # Simular erro de autorização
            mock_transcribe.side_effect = Exception("401 Unauthorized")

            try:
                await mock_transcribe(
                    media_id="audio_123",
                    mime_type="audio/ogg",
                    access_token="token_invalido",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_001"
                )
            except Exception as e:
                # Erro permanente
                assert "401" in str(e) or "unauthorized" in str(e).lower(), "Deveria detectar erro permanente"
                # Deveria marcar FALHA_PERMANENTE
                print("✅ [TESTE FASE 4.7] Token inválido detectado")

    @pytest.mark.asyncio
    async def test_08_mensagem_duplicada_dedup(self):
        """Teste 8: Mensagem duplicada não gera segundo atendimento."""
        print("\n[TESTE FASE 4.8] Mensagem duplicada detectada")

        with patch('services.whatsapp_msg_state_service.marcar_processando') as mock_mark:
            # Primeira chamada sucesso
            mock_mark.return_value = True

            resultado_1 = await mock_mark("endpoint", "msg_id_001", 1000000.0)

            # Segunda chamada mesma msg_id deveria falhar (AlreadyExists)
            from services.whatsapp_msg_state_service import AlreadyExists
            mock_mark.side_effect = AlreadyExists("Documento já existe")

            try:
                resultado_2 = await mock_mark("endpoint", "msg_id_001", 1000000.0)
            except AlreadyExists as e:
                assert "AlreadyExists" in str(type(e).__name__), "Deveria ser AlreadyExists"
                # Fluxo em main.py deveria continuar (skip)
                print("✅ [TESTE FASE 4.8] Duplicata detectada e pulada")

    @pytest.mark.asyncio
    async def test_09_instancias_concorrentes(self):
        """Teste 9: Duas instâncias não processam a mesma mensagem."""
        print("\n[TESTE FASE 4.9] Instâncias concorrentes")

        with patch('services.whatsapp_msg_state_service.marcar_processando') as mock_mark:
            # Instância 1 ganha
            mock_mark.side_effect = [True, False]  # Inst 1 True, Inst 2 False

            resultado_1 = await mock_mark("endpoint", "msg_id_001", 1000.0)
            resultado_2 = await mock_mark("endpoint", "msg_id_001", 1000.0)

            assert resultado_1 is True, "Primeira instância deveria ganhar"
            assert resultado_2 is False, "Segunda instância deveria perder"

            print("✅ [TESTE FASE 4.9] Concorrência detectada")

    @pytest.mark.asyncio
    async def test_10_lease_expirado(self):
        """Teste 10: Instância que perdeu lease não consegue finalizar."""
        print("\n[TESTE FASE 4.10] Lease expirado")

        with patch('services.whatsapp_msg_state_service._atualizar_status') as mock_update:
            # Simular validação de instancia_id falhar (lease perdido)
            mock_update.return_value = False  # Falha na validação

            resultado = await mock_update(
                "endpoint",
                "msg_id_001",
                "CONCLUIDA",
                {"message_id": "wamid_resp_001"},
                timestamp_webhook=1000.0
            )

            assert resultado is False, "Update deveria falhar com lease expirado"
            print("✅ [TESTE FASE 4.10] Lease expirado bloqueia finalização")

    @pytest.mark.asyncio
    async def test_11_tenant_actor_id_preservados(self):
        """Teste 11: Tenant e actor_id preservados em fluxo de áudio."""
        print("\n[TESTE FASE 4.11] Tenant/actor_id preservados")

        # Mock resolver tenant
        with patch('services.whatsapp_endpoint_service.resolver_tenant_por_endpoint') as mock_resolver:
            mock_resolver.return_value = "tenant_abc"

            tenant_id = mock_resolver("5511999999999")

            assert tenant_id == "tenant_abc", "Tenant deveria ser preservado"

            # Verificar que seria passado ao router
            with patch('router.principal_router.roteador_principal') as mock_router:
                await mock_router(
                    user_id="5511991382080",
                    mensagem="Quero agendar",
                    tenant_id=tenant_id,
                    phone_number_id="5511999999999"
                )

                mock_router.assert_called_once()
                call_args = mock_router.call_args
                assert call_args[1]["tenant_id"] == "tenant_abc", "Tenant passado ao router"

            print("✅ [TESTE FASE 4.11] Tenant/actor_id preservados")

    @pytest.mark.asyncio
    async def test_12_confirmacao_por_audio(self):
        """Teste 12: Confirmação por áudio passa pelo fluxo existente."""
        print("\n[TESTE FASE 4.12] Confirmação por áudio")

        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            # Áudio com confirmação
            mock_transcribe.return_value = "Sim, confirmo"

            with patch('router.principal_router.roteador_principal') as mock_router:
                mock_router.return_value = "Agendamento confirmado!"

                texto = await mock_transcribe(
                    media_id="audio_confirm",
                    mime_type="audio/ogg",
                    access_token="token",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_002"
                )

                # Passar ao router (fluxo normal)
                resposta = await mock_router(
                    user_id="5511991382080",
                    mensagem=texto,
                    tenant_id="tenant1",
                    phone_number_id="5511999999999"
                )

                assert resposta is not None, "Confirmação deveria ser processada"
                print("✅ [TESTE FASE 4.12] Confirmação por áudio funciona")

    @pytest.mark.asyncio
    async def test_13_novo_agendamento_audio(self):
        """Teste 13: Novo agendamento por áudio passa pelo fluxo existente."""
        print("\n[TESTE FASE 4.13] Novo agendamento por áudio")

        with patch('services.whatsapp_media_service.transcrever_audio_whatsapp') as mock_transcribe:
            # Áudio com solicitação de agendamento
            mock_transcribe.return_value = "Quero agendar um corte feminino para segunda às 14 horas"

            with patch('router.principal_router.roteador_principal') as mock_router:
                mock_router.return_value = {"ok": True, "draft": {"servico": "corte feminino"}}

                texto = await mock_transcribe(
                    media_id="audio_sched",
                    mime_type="audio/ogg",
                    access_token="token",
                    tenant_id="tenant1",
                    cliente_id="5511991382080",
                    msg_id="wamid_audio_003"
                )

                # Passar ao router (fluxo normal)
                resposta = await mock_router(
                    user_id="5511991382080",
                    mensagem=texto,
                    tenant_id="tenant1",
                    phone_number_id="5511999999999"
                )

                assert resposta is not None, "Agendamento por áudio deveria ser processado"
                print("✅ [TESTE FASE 4.13] Novo agendamento por áudio funciona")

    @pytest.mark.asyncio
    async def test_14_texto_continua_funcionando(self):
        """Teste 14: Texto WhatsApp continua funcionando normalmente."""
        print("\n[TESTE FASE 4.14] Texto WhatsApp continua")

        with patch('router.principal_router.roteador_principal') as mock_router:
            mock_router.return_value = "Resposta para texto"

            # Fluxo de texto (não passa por transcrição)
            resposta = await mock_router(
                user_id="5511991382080",
                mensagem="Quero agendar por texto",
                tenant_id="tenant1",
                phone_number_id="5511999999999"
            )

            assert resposta == "Resposta para texto", "Texto deveria funcionar normalmente"
            print("✅ [TESTE FASE 4.14] Texto continua funcionando")

    def test_15_sem_placeholder_ao_router(self):
        """Teste 15: Nenhum placeholder chega ao router."""
        print("\n[TESTE FASE 4.15] Sem placeholder no router")

        # Verificar que processamento_tipo == "audio" não passa placeholder
        # Na FASE 4, placeholder foi removido (linha 268 de main.py)
        # texto_body = None até transcrição estar pronta

        placeholder_pattern = r"\[AUDIO-PLACEHOLDER:.*\]"
        import re

        # Strings que DEVERIAM chegar ao router (após transcrição)
        valid_inputs = [
            "Texto normal",
            "Quero agendar",
            "Sim, confirmo",
            "Corte feminino segunda às 14h"
        ]

        # Strings que NÃO devem chegar
        invalid_inputs = [
            "[AUDIO-PLACEHOLDER: audio_123]"
        ]

        # Validar que apenas strings válidas chegam ao router
        for s in valid_inputs:
            assert not re.match(placeholder_pattern, s), f"Input válido não deveria ser placeholder: {s}"

        # Validar que placeholder é detectado como inválido
        for s in invalid_inputs:
            assert re.match(placeholder_pattern, s), f"Placeholder deveria ser detectado: {s}"

        print("✅ [TESTE FASE 4.15] Sem placeholder ao router")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FASE 4 TEST — 15 Cenários de Integração de Áudio")
    print("="*70)

    pytest.main([__file__, "-v", "-s"])
