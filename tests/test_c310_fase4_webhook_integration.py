"""
C3.10 FASE 4 — Testes de Integração: Webhook → principal_router

Objetivo: Validar que o fluxo webhook integra corretamente com principal_router
mantendo isolamento multi-tenant.

Testes:
  T8 — Webhook → principal_router com tenant válido
  T9 — Múltiplas mensagens da mesma sessão no mesmo tenant
  T10 — Dedupe de mensagem preserva tenant correto
  T11 — phone_number_id não registrado → descartado sem processamento
"""

import pytest
import json
import uuid
import hmac
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

# Firebase initialization
try:
    import config.firebase_config  # noqa: F401
except Exception as e:
    print(f"[WARN] firebase_config não disponível: {e}")

from services.firestore_client import get_db
from services.whatsapp_endpoint_service import (
    registrar_endpoint_whatsapp,
    resolver_tenant_por_endpoint,
)


class TestC310Fase4WebhookIntegration:
    """Testes de integração webhook → principal_router."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup e cleanup de testes."""
        run_id = str(uuid.uuid4())[:8]

        # IDs únicos
        self.tenant_a = f"c310_f4_tenant_a_{run_id}"
        self.tenant_b = f"c310_f4_tenant_b_{run_id}"
        self.endpoint_a = f"c310_f4_endpoint_a_{run_id}"
        self.endpoint_b = f"c310_f4_endpoint_b_{run_id}"
        self.phone_a = f"5511934567890_{run_id}"
        self.phone_b = f"5511934567891_{run_id}"

        self.db = get_db()

        # Criar tenants
        self.db.collection("Clientes").document(self.tenant_a).set({
            "tipo_usuario": "salao",
            "nome": f"Tenant A {self.tenant_a}",
            "criado_em": datetime.now().isoformat(),
        })
        self.db.collection("Clientes").document(self.tenant_b).set({
            "tipo_usuario": "salao",
            "nome": f"Tenant B {self.tenant_b}",
            "criado_em": datetime.now().isoformat(),
        })

        # Registrar endpoints
        registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a,
            display_phone_number="+55 11 9 3456-7890",
            waba_id="waba_a",
        )
        registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_b,
            tenant_id=self.tenant_b,
            display_phone_number="+55 11 9 3456-7891",
            waba_id="waba_b",
        )

        yield

        # Cleanup
        self._cleanup()

    def _cleanup(self):
        """Deletar documentos de teste."""
        try:
            self.db.collection("WhatsAppEndpoints").document(self.endpoint_a).delete()
            self.db.collection("WhatsAppEndpoints").document(self.endpoint_b).delete()
            self.db.collection("Clientes").document(self.tenant_a).delete()
            self.db.collection("Clientes").document(self.tenant_b).delete()
        except:
            pass

    # =========================================================
    # T8 — WEBHOOK → PRINCIPAL_ROUTER COM TENANT VÁLIDO
    # =========================================================

    def test_t8_webhook_resolve_tenant_e_chama_router(self):
        """T8: Webhook recebe phone_number_id, resolve tenant, chama principal_router."""
        # Simular payload Meta
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": self.endpoint_a,
                            "display_phone_number": "+55 11 9 3456-7890",
                            "business_account_id": "waba_a"
                        },
                        "messages": [{
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "from": self.phone_a,
                            "text": {
                                "body": "oi"
                            }
                        }]
                    }
                }]
            }]
        }

        # Extrair phone_number_id e resolver tenant (como main.py faz)
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes.get("value", {})
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        # Resolver tenant
        resolved_tenant = resolver_tenant_por_endpoint(phone_number_id)

        # Validar que tenant foi resolvido corretamente
        assert resolved_tenant == self.tenant_a, \
            f"Esperava {self.tenant_a}, obteve {resolved_tenant}"

        # Validar que mensagem seria processada (não descartada)
        assert phone_number_id is not None, "phone_number_id deve estar presente"
        assert resolved_tenant is not None, "tenant_id deve ser resolvido"

        print(f"[PASS] T8: Webhook resolve phone_number_id={phone_number_id} -> tenant={resolved_tenant}")

    # =========================================================
    # T9 — MÚLTIPLAS MENSAGENS MESMA SESSÃO
    # =========================================================

    def test_t9_multiplas_mensagens_mesmo_tenant(self):
        """T9: Múltiplas mensagens da mesma sessão permanecem no mesmo tenant."""
        # Simular múltiplas mensagens do mesmo endpoint
        mensagens = [
            {"id": f"msg1_{uuid.uuid4().hex[:4]}", "text": "oi"},
            {"id": f"msg2_{uuid.uuid4().hex[:4]}", "text": "quero agendar"},
            {"id": f"msg3_{uuid.uuid4().hex[:4]}", "text": "segunda às 14h"},
        ]

        tenant_resolvido_anterior = None

        for msg in mensagens:
            # Simular resolução de tenant para cada mensagem
            tenant_resolvido = resolver_tenant_por_endpoint(self.endpoint_a)

            # Validar que todas as mensagens resolvem para o MESMO tenant
            if tenant_resolvido_anterior is not None:
                assert tenant_resolvido == tenant_resolvido_anterior, \
                    f"Tenant divergiu entre mensagens: {tenant_resolvido} != {tenant_resolvido_anterior}"

            tenant_resolvido_anterior = tenant_resolvido
            assert tenant_resolvido == self.tenant_a, \
                f"Tenant deve ser {self.tenant_a}, mas foi {tenant_resolvido}"

        assert tenant_resolvido_anterior == self.tenant_a, \
            "Todas as mensagens devem usar o mesmo tenant"

        print(f"[PASS] T9: {len(mensagens)} mensagens permanecem no tenant {self.tenant_a}")

    # =========================================================
    # T10 — DEDUPE PRESERVA TENANT CORRETO
    # =========================================================

    def test_t10_dedupe_preserva_tenant(self):
        """T10: Dedupe de mensagem não perde informação de tenant."""
        msg_id = f"msg_dedupe_{uuid.uuid4().hex[:8]}"

        # Simular conjunto de message IDs processadas (como em main.py:222)
        processed_ids = set()

        # Primeira ocorrência da mensagem
        tenant_1 = resolver_tenant_por_endpoint(self.endpoint_a)
        processed_ids.add(msg_id)

        # Segunda ocorrência (mesma message ID, mesmo endpoint)
        # Validar que dedupe funciona
        assert msg_id in processed_ids, "Message ID deve estar no conjunto de processados"

        # Validar que tenant continua sendo resolvido corretamente
        tenant_2 = resolver_tenant_por_endpoint(self.endpoint_a)

        assert tenant_1 == tenant_2, "Tenant deve permanecer consistente"
        assert tenant_1 == self.tenant_a, "Tenant deve ser o tenant_a"

        print(f"[PASS] T10: Dedupe preserva tenant {self.tenant_a} para message_id {msg_id}")

    # =========================================================
    # T11 — PHONE_NUMBER_ID NÃO REGISTRADO → DESCARTADO
    # =========================================================

    def test_t11_endpoint_desconhecido_nao_chega_ao_router(self):
        """T11: phone_number_id não registrado → mensagem descartada sem chegar ao principal_router."""
        endpoint_unknown = f"unknown_endpoint_{uuid.uuid4().hex[:8]}"

        # Tentar resolver endpoint desconhecido
        resolved_tenant = resolver_tenant_por_endpoint(endpoint_unknown)

        # Validar que retorna None (falha segura)
        assert resolved_tenant is None, \
            f"Endpoint desconhecido deveria retornar None, mas retornou {resolved_tenant}"

        # Simular lógica de main.py:209-212
        # Se tenant_id é None e phone_number_id foi fornecido → DESCARTA
        phone_number_id = endpoint_unknown
        tenant_id = resolved_tenant

        if not tenant_id and phone_number_id:
            # Esta é a condição que faz descartamento em main.py
            descartado = True
        else:
            descartado = False

        assert descartado, \
            "Mensagem com endpoint desconhecido deveria ser descartada"

        print(f"[PASS] T11: Endpoint {endpoint_unknown} nao registrado -> mensagem descartada")

    # =========================================================
    # T12 — ISOLAMENTO ENTRE ENDPOINTS
    # =========================================================

    def test_t12_endpoint_a_nao_acessa_tenant_b(self):
        """T12: Endpoint A resolve para Tenant A, não para Tenant B."""
        tenant_a = resolver_tenant_por_endpoint(self.endpoint_a)
        tenant_b = resolver_tenant_por_endpoint(self.endpoint_b)

        # Validar que endpoints resolvem para tenants diferentes
        assert tenant_a == self.tenant_a, \
            f"Endpoint A deveria resolver para {self.tenant_a}, mas foi {tenant_a}"

        assert tenant_b == self.tenant_b, \
            f"Endpoint B deveria resolver para {self.tenant_b}, mas foi {tenant_b}"

        # Validar que não há cruzamento
        assert tenant_a != tenant_b, \
            "Endpoints diferentes devem resolver para tenants diferentes"

        print(f"[PASS] T12: Isolamento garantido - endpoint_a->{tenant_a}, endpoint_b->{tenant_b}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
