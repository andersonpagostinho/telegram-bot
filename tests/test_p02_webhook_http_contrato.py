"""
P0.2: VALIDAÇÃO CONTRATO HTTP WEBHOOK WHATSAPP

Testes para validar que webhook retorna HTTP válido (não inteiro isolado).
Foco: Contrato HTTP, não lógica de processamento.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


class TestWebhookHTTPContrato:
    """Testes de contrato HTTP para o webhook"""

    @pytest.fixture
    def app_client(self):
        """Fixture para cliente Flask"""
        from main import app
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def valid_payload(self):
        """Payload WhatsApp válido"""
        return {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511991382080",
                            "business_account_id": "123"
                        },
                        "messages": [{
                            "id": "msg_test_001",
                            "from": "5511991382080",
                            "type": "text",
                            "text": {"body": "Olá"}
                        }]
                    }
                }]
            }]
        }

    # === TESTE 1: Webhook válido retorna HTTP 200 ===
    @pytest.mark.asyncio
    async def test_01_webhook_valido_retorna_http_200(self, app_client, valid_payload):
        """✅ Webhook válido deve retornar HTTP 200 (não 500)"""
        with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
            with patch("services.whatsapp_endpoint_service.resolver_tenant_por_endpoint") as mock_tenant:
                mock_mark.return_value = True
                mock_tenant.return_value = "tenant_123"

                response = app_client.post(
                    "/webhook/whatsapp",
                    data=json.dumps(valid_payload),
                    content_type="application/json",
                    headers={"X-Hub-Signature-256": "sha256=dummy"}
                )

                # Verificar HTTP 200 válido (não 500)
                assert response.status_code == 200, f"Esperado 200, recebido {response.status_code}"
                assert response.data is not None

    # === TESTE 2: Quota (linha 329 corrigida) → HTTP 200 ===
    @pytest.mark.asyncio
    async def test_02_quota_retorna_http_200(self, app_client, valid_payload):
        """✅ Erro Quota ao marcar deve retornar HTTP 200 (não 500)"""
        with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
            # Simular Quota error
            mock_mark.side_effect = Exception("429: Quota exceeded on document")

            response = app_client.post(
                "/webhook/whatsapp",
                data=json.dumps(valid_payload),
                content_type="application/json",
                headers={"X-Hub-Signature-256": "sha256=dummy"}
            )

            # HTTP 200 válido (linha 329 corrigida)
            assert response.status_code == 200, f"Esperado 200 para Quota, recebido {response.status_code}"

    # === TESTE 3: Erro genérico (linha 333 corrigida) → HTTP 200 ===
    @pytest.mark.asyncio
    async def test_03_erro_generico_retorna_http_200(self, app_client, valid_payload):
        """✅ Erro genérico ao adquirir deve retornar HTTP 200 (não 500)"""
        with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
            # Simular erro genérico
            mock_mark.side_effect = Exception("Firestore error ao adquirir mensagem")

            response = app_client.post(
                "/webhook/whatsapp",
                data=json.dumps(valid_payload),
                content_type="application/json",
                headers={"X-Hub-Signature-256": "sha256=dummy"}
            )

            # HTTP 200 válido (linha 333 corrigida)
            assert response.status_code == 200, f"Esperado 200 para erro genérico, recebido {response.status_code}"

    # === TESTE 4: Duplicada (linha 337 corrigida) → HTTP 200 ===
    @pytest.mark.asyncio
    async def test_04_duplicada_retorna_http_200(self, app_client, valid_payload):
        """✅ Mensagem duplicada (AlreadyExists) deve retornar HTTP 200 (não 500)"""
        with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
            # Simular AlreadyExists (outra instância processando)
            mock_mark.side_effect = Exception("AlreadyExists: mensagem já em processamento")

            response = app_client.post(
                "/webhook/whatsapp",
                data=json.dumps(valid_payload),
                content_type="application/json",
                headers={"X-Hub-Signature-256": "sha256=dummy"}
            )

            # HTTP 200 válido (linha 337 corrigida)
            assert response.status_code == 200, f"Esperado 200 para AlreadyExists, recebido {response.status_code}"

    # === TESTE 5: JSON inválido → HTTP 200 ===
    @pytest.mark.asyncio
    async def test_05_json_invalido_retorna_http_200(self, app_client):
        """✅ JSON inválido deve retornar HTTP 200 (deixa Meta retentar)"""
        response = app_client.post(
            "/webhook/whatsapp",
            data="{ invalid json",
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=dummy"}
        )

        # HTTP 200 válido (linha 714 já estava correto)
        assert response.status_code == 200, f"Esperado 200 para JSON inválido, recebido {response.status_code}"

    # === TESTE 6: Entrada sem mensagens → HTTP 200 ===
    @pytest.mark.asyncio
    async def test_06_entrada_vazia_retorna_http_200(self, app_client):
        """✅ Entrada sem mensagens deve retornar HTTP 200"""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511991382080"
                        },
                        "messages": []  # Vazio
                    }
                }]
            }]
        }

        response = app_client.post(
            "/webhook/whatsapp",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=dummy"}
        )

        # HTTP 200 válido
        assert response.status_code == 200, f"Esperado 200 para entrada vazia, recebido {response.status_code}"

    # === TESTE 7: Validação assinatura falha → HTTP 403 ===
    @pytest.mark.asyncio
    async def test_07_assinatura_invalida_retorna_http_403(self, app_client, valid_payload):
        """✅ Assinatura inválida deve retornar HTTP 403"""
        response = app_client.post(
            "/webhook/whatsapp",
            data=json.dumps(valid_payload),
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=invalid"}
        )

        # HTTP 403 (não 500)
        assert response.status_code == 403, f"Esperado 403 para assinatura inválida, recebido {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
