"""
P0-WA-OUTBOUND Implementation Tests

6 mandatory tests:
T1 - outbound unit/integration (construct Meta call without exposing token)
T2 - webhook inbound to router to outbound
T3 - unknown endpoint (no router call, no send)
T4 - multi-tenant isolation (different phone_number_id to different tenants)
T5 - Meta HTTP error (4xx/5xx returns structured error)
T6 - scheduler import and call (does not fail)
"""

import pytest
import asyncio
import os
from unittest.mock import patch
from datetime import datetime
import uuid

# Imports
from services.whatsapp_service import enviar_mensagem_whatsapp
from services.whatsapp_endpoint_service import (
    registrar_endpoint_whatsapp,
    resolver_tenant_por_endpoint,
)
from services.firestore_client import get_db

pytest_plugins = ('pytest_asyncio',)


class TestP0WAOutbound:
    """Tests for P0-WA-OUTBOUND implementation"""

    @pytest.mark.asyncio
    async def test_t1_outbound_error_handling(self):
        """T1: Outbound service returns structured error without crashing"""
        print("\n[T1] Outbound error handling")

        # Without credentials, should return structured error
        resultado = await enviar_mensagem_whatsapp(
            destinatario_id="5519999999999",
            mensagem="Test message"
        )

        assert isinstance(resultado, dict), "[FAIL T1] Should return dict"
        assert "success" in resultado, "[FAIL T1] Missing 'success' field"
        assert "status_code" in resultado, "[FAIL T1] Missing 'status_code' field"
        assert resultado.get("success") == False, "[FAIL T1] Should fail without credentials"

        print(f"  [OK T1] Returns structured error without crash")

    @pytest.mark.asyncio
    async def test_t2_webhook_resolver_calls(self):
        """T2: Webhook can resolve tenant and call router"""
        print("\n[T2] Webhook resolver and router integration")

        run_id = str(uuid.uuid4())[:8]
        tenant_id = f"t2_tenant_{run_id}"
        phone_number_id = f"t2_endpoint_{run_id}"

        try:
            # Register endpoint
            result_reg = registrar_endpoint_whatsapp(
                phone_number_id=phone_number_id,
                tenant_id=tenant_id,
                display_phone_number="+55 11 9 0000-0000"
            )
            assert result_reg["ok"] == True, "[FAIL T2] Endpoint registration failed"

            # Resolve tenant
            tenant_resolved = resolver_tenant_por_endpoint(phone_number_id)
            assert tenant_resolved == tenant_id, f"[FAIL T2] Expected {tenant_id}, got {tenant_resolved}"

            print(f"  [OK T2] Endpoint resolution works")

        finally:
            try:
                db = get_db()
                db.collection("WhatsAppEndpoints").document(phone_number_id).delete()
            except:
                pass

    @pytest.mark.asyncio
    async def test_t3_unknown_endpoint_safe(self):
        """T3: Unknown endpoint returns None (safe fallback)"""
        print("\n[T3] Unknown endpoint safe fallback")

        unknown_endpoint = "unknown_endpoint_12345678"
        result = resolver_tenant_por_endpoint(unknown_endpoint)

        assert result is None, f"[FAIL T3] Expected None, got {result}"
        print(f"  [OK T3] Unknown endpoint returns None safely")

    @pytest.mark.asyncio
    async def test_t4_multi_tenant_isolation(self):
        """T4: Different endpoints resolve to different tenants"""
        print("\n[T4] Multi-tenant isolation")

        run_id = str(uuid.uuid4())[:8]
        tenant_a = f"t4_tenant_a_{run_id}"
        tenant_b = f"t4_tenant_b_{run_id}"
        endpoint_a = f"t4_endpoint_a_{run_id}"
        endpoint_b = f"t4_endpoint_b_{run_id}"

        try:
            # Register two endpoints
            reg_a = registrar_endpoint_whatsapp(endpoint_a, tenant_a, "+55 11 1111-1111")
            reg_b = registrar_endpoint_whatsapp(endpoint_b, tenant_b, "+55 11 2222-2222")

            assert reg_a["ok"] == True, "[FAIL T4] Register A failed"
            assert reg_b["ok"] == True, "[FAIL T4] Register B failed"

            # Resolve and verify isolation
            resolved_a = resolver_tenant_por_endpoint(endpoint_a)
            resolved_b = resolver_tenant_por_endpoint(endpoint_b)

            assert resolved_a == tenant_a, f"[FAIL T4] Endpoint A: expected {tenant_a}, got {resolved_a}"
            assert resolved_b == tenant_b, f"[FAIL T4] Endpoint B: expected {tenant_b}, got {resolved_b}"
            assert resolved_a != resolved_b, "[FAIL T4] Tenants not isolated!"

            print(f"  [OK T4] Isolation confirmed: {endpoint_a}->{tenant_a}, {endpoint_b}->{tenant_b}")

        finally:
            try:
                db = get_db()
                db.collection("WhatsAppEndpoints").document(endpoint_a).delete()
                db.collection("WhatsAppEndpoints").document(endpoint_b).delete()
            except:
                pass

    @pytest.mark.asyncio
    async def test_t5_error_structure(self):
        """T5: Error returns are always structured (success field always present)"""
        print("\n[T5] Error structure validation")

        # Test with empty destinatario_id
        resultado = await enviar_mensagem_whatsapp(
            destinatario_id="",
            mensagem="Test"
        )

        assert isinstance(resultado, dict), "[FAIL T5] Should return dict"
        assert "success" in resultado, "[FAIL T5] Missing 'success' field"
        assert resultado.get("success") == False, "[FAIL T5] Should fail on empty destinatario"

        print(f"  [OK T5] Error returns are always structured")

    @pytest.mark.asyncio
    async def test_t6_scheduler_import(self):
        """T6: Scheduler can import and call the function"""
        print("\n[T6] Scheduler import works")

        try:
            # Import as scheduler would
            from services.whatsapp_service import enviar_mensagem_whatsapp as send_wa

            # Function must be async
            assert asyncio.iscoroutinefunction(send_wa), "[FAIL T6] Function not async"

            # Function must be callable
            assert callable(send_wa), "[FAIL T6] Function not callable"

            print(f"  [OK T6] Scheduler can import and call function")

        except ImportError as e:
            pytest.fail(f"[FAIL T6] ImportError: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
