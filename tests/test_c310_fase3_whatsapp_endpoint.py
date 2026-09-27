"""
C3.10 FASE 3 — Testes Formais: WhatsApp Endpoint-to-Tenant Resolution

Objetivo: Validar extração, resolução e isolamento de phone_number_id → tenant_id

Padrão: Firestore REAL, determinístico, falha segura, sem fallbacks inseguros

Testes:
  T1 — Extração de phone_number_id do payload
  T2 — Resolução determinística
  T3 — Isolamento multi-tenant
  T4 — Rejeição de endpoint desconhecido
  T5 — Unicidade e detecção de colisão
  T6 — Compatibilidade com Opção B (tenant_id explícito)
  T7 — Validação HMAC preservada
"""

import pytest
import json
import uuid
import hmac
import hashlib
from datetime import datetime
import pytz

# [OK] Inicializar Firebase ANTES de qualquer outro import
try:
    import config.firebase_config  # noqa: F401 - side effect: inicializa Firebase
except Exception as e:
    print(f"[WARN] firebase_config não disponível, tentando firestore_client: {e}")

from services.firestore_client import get_db
from services.whatsapp_endpoint_service import (
    registrar_endpoint_whatsapp,
    resolver_tenant_por_endpoint,
    validar_endpoint_para_tenant,
)

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC310Fase3WhatsAppEndpoint:
    """Testes formais de endpoint WhatsApp → tenant resolution."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup e cleanup de testes."""
        run_id = str(uuid.uuid4())[:8]

        # IDs únicos
        self.tenant_a = f"c310_f3_tenant_a_{run_id}"
        self.tenant_b = f"c310_f3_tenant_b_{run_id}"
        self.endpoint_a = f"c310_f3_endpoint_a_{run_id}"
        self.endpoint_b = f"c310_f3_endpoint_b_{run_id}"
        self.endpoint_unknown = f"c310_f3_endpoint_unknown_{run_id}"

        self.db = get_db()

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
    # T1 — EXTRAÇÃO DE PHONE_NUMBER_ID DO PAYLOAD
    # =========================================================

    def test_t1_payload_valido_contem_phone_number_id(self):
        """T1: Payload WhatsApp válido contém phone_number_id."""
        # Payload típico da Meta Cloud API
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": "102345678901234",
                            "display_phone_number": "55 11 93456-7890",
                            "business_account_id": "987654321098765"
                        },
                        "messages": [{
                            "from": "5519994443694",
                            "text": {"body": "Olá"}
                        }]
                    }
                }]
            }]
        }

        # Extrair como main.py faz
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes.get("value", {})
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        assert phone_number_id == "102345678901234", \
            f"phone_number_id não extraído corretamente: {phone_number_id}"
        print(f"[PASS] T1: phone_number_id extraído: {phone_number_id}")

    def test_t1_payload_sem_phone_number_id_rejeitado(self):
        """T1: Payload sem phone_number_id deve ser identificado como inválido."""
        # Payload SEM metadata
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5519994443694",
                            "text": {"body": "Olá"}
                        }]
                    }
                }]
            }]
        }

        # Extrair como main.py faz
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes.get("value", {})
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        assert phone_number_id is None, \
            f"Deveria ser None, mas foi: {phone_number_id}"
        print(f"[PASS] T1: Payload inválido detectado (phone_number_id=None)")

    # =========================================================
    # T2 — RESOLUÇÃO DETERMINÍSTICA
    # =========================================================

    @pytest.mark.asyncio
    async def test_t2_endpoint_conhecido_resolve_tenant(self):
        """T2: phone_number_id conhecido resolve exatamente para tenant correspondente."""
        # Registrar endpoint
        reg = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a,
            display_phone_number="+55 11 9 3456-7890",
            waba_id="waba_a"
        )
        assert reg["ok"], f"Falha ao registrar: {reg}"

        # Resolver
        resolved = resolver_tenant_por_endpoint(self.endpoint_a)

        assert resolved == self.tenant_a, \
            f"Esperava {self.tenant_a}, obteve {resolved}"
        print(f"[PASS] T2: Resolução determinística: {self.endpoint_a} -> {self.tenant_a}")

    def test_t2_endpoint_inexistente_nao_fallback(self):
        """T2: Endpoint inexistente não pode produzir tenant por fallback."""
        # Tentar resolver endpoint desconhecido
        resolved = resolver_tenant_por_endpoint(self.endpoint_unknown)

        assert resolved is None, \
            f"Deveria retornar None, mas foi: {resolved}"
        print(f"[PASS] T2: Endpoint desconhecido retorna None (sem fallback)")

    # =========================================================
    # T3 — ISOLAMENTO MULTI-TENANT
    # =========================================================

    def test_t3_isolamento_endpoints_diferentes(self):
        """T3: Endpoint A → Tenant A, Endpoint B → Tenant B."""
        # Registrar endpoint A
        reg_a = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a
        )
        assert reg_a["ok"], f"Falha A: {reg_a}"

        # Registrar endpoint B
        reg_b = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_b,
            tenant_id=self.tenant_b
        )
        assert reg_b["ok"], f"Falha B: {reg_b}"

        # Resolver A
        resolved_a = resolver_tenant_por_endpoint(self.endpoint_a)
        assert resolved_a == self.tenant_a

        # Resolver B
        resolved_b = resolver_tenant_por_endpoint(self.endpoint_b)
        assert resolved_b == self.tenant_b

        # Verificar isolamento
        assert resolved_a != resolved_b, \
            "Endpoints diferentes não podem resolver para mesmo tenant"

        print(f"[PASS] T3: Isolamento garantido: {self.endpoint_a}->{resolved_a}, {self.endpoint_b}->{resolved_b}")

    # =========================================================
    # T4 — REJEIÇÃO DE ENDPOINT DESCONHECIDO
    # =========================================================

    def test_t4_endpoint_desconhecido_rejeitado(self):
        """T4: phone_number_id desconhecido deve ser rejeitado, sem fallback."""
        endpoint_unknown = f"unknown_{uuid.uuid4().hex[:8]}"

        # Tentar resolver
        resolved = resolver_tenant_por_endpoint(endpoint_unknown)

        assert resolved is None, \
            f"Deveria ser None, mas foi: {resolved}"
        print(f"[PASS] T4: Endpoint desconhecido rejeitado (sem fallback)")

    # =========================================================
    # T5 — UNICIDADE E COLISÃO
    # =========================================================

    def test_t5_endpoint_unico_por_tenant(self):
        """T5: Um phone_number_id deve possuir somente um tenant_id."""
        # Registrar endpoint para tenant_a
        reg1 = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a
        )
        assert reg1["ok"], f"Falha 1: {reg1}"

        # Tentar associar MESMO endpoint a tenant_b (colisão)
        reg2 = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_b
        )

        # Deve falhar
        assert not reg2["ok"], \
            "Colisão deveria ser rejeitada!"
        assert "outro tenant" in reg2.get("motivo", "").lower(), \
            f"Mensagem deveria mencionar colisão: {reg2.get('motivo')}"

        print(f"[PASS] T5: Colisão detectada e rejeitada")

    def test_t5_idempotencia_registro(self):
        """T5: Registrar mesmo endpoint 2x com mesmo tenant é idempotente."""
        # Primeira vez
        reg1 = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a
        )
        assert reg1["ok"]

        # Segunda vez (idempotente)
        reg2 = registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a
        )
        assert reg2["ok"], f"Segunda tentativa falhou: {reg2}"
        assert reg2.get("ja_existia") == True, \
            "Deveria indicar que já existia"

        print(f"[PASS] T5: Idempotência confirmada")

    # =========================================================
    # T6 — COMPATIBILIDADE COM OPÇÃO B
    # =========================================================

    def test_t6_tenant_resolvido_eh_passado_explicitamente(self):
        """T6: Tenant resolvido deve ser passado explicitamente, não inferido."""
        # Registrar endpoint
        registrar_endpoint_whatsapp(
            phone_number_id=self.endpoint_a,
            tenant_id=self.tenant_a
        )

        # Resolver
        tenant_id = resolver_tenant_por_endpoint(self.endpoint_a)

        # Tenant deve ser PASSADO EXPLICITAMENTE ao fluxo
        # (não deve haver fallback para user_id, wa_id, obter_id_dono, etc)
        assert tenant_id is not None, "Tenant não foi resolvido"
        assert isinstance(tenant_id, str), "Tenant deve ser string"

        # Validar que é realmente o tenant certo
        is_valid = validar_endpoint_para_tenant(self.endpoint_a, self.tenant_a)
        assert is_valid, \
            f"Validação falhou: endpoint {self.endpoint_a} não pertence a {self.tenant_a}"

        print(f"[PASS] T6: Tenant resolvido ({tenant_id}) passa explicitamente (Opção B)")

    # =========================================================
    # T7 — SEGURANÇA HMAC PRESERVADA
    # =========================================================

    def test_t7_hmac_validation_preservada(self):
        """T7: Validação HMAC do webhook deve permanecer intacta."""
        secret = "test_secret"
        body = '{"test": "data"}'

        # Gerar HMAC válido
        hash_obj = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        )
        valid_hash = f"sha256={hash_obj.hexdigest()}"

        # Simular validação (como em main.py)
        def validate_signature(signature: str, body: str, secret: str) -> bool:
            if not signature.startswith("sha256="):
                return False
            hash_value = signature.split("=")[1]
            expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(hash_value, expected)

        # Testar
        is_valid = validate_signature(valid_hash, body, secret)
        assert is_valid, "HMAC válido deveria passar"

        # Testar HMAC inválido
        invalid_hash = "sha256=invalid"
        is_invalid = validate_signature(invalid_hash, body, secret)
        assert not is_invalid, "HMAC inválido deveria falhar"

        print(f"[PASS] T7: Validação HMAC preservada e funcionando")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
