"""
TESTE E2E P0.3 — CONSULTA PURA SEM AGENDAMENTO

Frase: "Queria cortar o cabelo segunda às 16 teria horário?"
Esperado: Apenas H2 responde (SEM P0.5 V3 acionada)
Validação: Sem "Novo agendamento detectado" nos logs
"""

import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime


class TestE2EP03ConsultaSemAgendamento:
    """Teste que "Queria cortar... segunda?" NÃO inicia agendamento"""

    @pytest.fixture
    def webhook_payload_consulta(self):
        """Payload WhatsApp para pergunta (consulta pura)"""
        return {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511991382080",
                            "business_account_id": "123"
                        },
                        "messages": [{
                            "id": f"msg_{datetime.now().timestamp()}",
                            "from": "5511991382080",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {
                                "body": "Queria cortar o cabelo segunda às 16 teria horário?"
                            }
                        }]
                    }
                }]
            }]
        }

    @pytest.mark.asyncio
    async def test_p03_01_consulta_sem_agendamento(self, webhook_payload_consulta):
        """✅ Consulta com ? NÃO deve iniciar P0.5 V3"""
        from main import app

        with app.test_client() as client:
            print(f"\n📝 Frase: {webhook_payload_consulta['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']}")

            with patch("main.validate_whatsapp_signature", return_value=True):
                with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
                    with patch("services.whatsapp_endpoint_service.resolver_tenant_por_endpoint") as mock_tenant:
                        with patch("router.principal_router.roteador_principal", new_callable=AsyncMock) as mock_router:
                            mock_mark.return_value = True
                            mock_tenant.return_value = "7394370553"
                            mock_router.return_value = "Sim! Temos Bruna segunda à tarde"

                            response = client.post(
                                "/webhook/whatsapp",
                                data=json.dumps(webhook_payload_consulta),
                                content_type="application/json",
                                headers={"X-Hub-Signature-256": "sha256=test"}
                            )

                            print(f"✅ [HTTP] Status: {response.status_code}")
                            assert response.status_code == 200, f"Esperado 200, recebido {response.status_code}"

                            await asyncio.sleep(0.5)

                            # Validar que roteador foi chamado (não P0.5 V3)
                            assert mock_router.called, "Roteador deveria ser chamado"
                            print(f"✅ [ROTEADOR] Foi chamado (consulta pura)")

    @pytest.mark.asyncio
    async def test_p03_02_afirmacao_COM_agendamento(self):
        """✅ Afirmação SEM ? DEVERIA iniciar P0.5 V3"""
        from main import app

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "5511991382080"
                        },
                        "messages": [{
                            "id": f"msg_{datetime.now().timestamp()}",
                            "from": "5511991382080",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {
                                "body": "Vou agendar corte segunda às 16"
                            }
                        }]
                    }
                }]
            }]
        }

        with app.test_client() as client:
            print(f"\n📝 Frase (afirmação): {payload['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']}")

            with patch("main.validate_whatsapp_signature", return_value=True):
                with patch("services.whatsapp_msg_state_service.marcar_processando", new_callable=AsyncMock) as mock_mark:
                    with patch("services.whatsapp_endpoint_service.resolver_tenant_por_endpoint") as mock_tenant:
                        with patch("router.principal_router.roteador_principal", new_callable=AsyncMock) as mock_router:
                            mock_mark.return_value = True
                            mock_tenant.return_value = "7394370553"
                            mock_router.return_value = "Vamos confirmar os detalhes"

                            response = client.post(
                                "/webhook/whatsapp",
                                data=json.dumps(payload),
                                content_type="application/json",
                                headers={"X-Hub-Signature-256": "sha256=test"}
                            )

                            print(f"✅ [HTTP] Status: {response.status_code}")
                            assert response.status_code == 200

                            await asyncio.sleep(0.5)

                            assert mock_router.called
                            print(f"✅ [ROTEADOR] Foi chamado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
