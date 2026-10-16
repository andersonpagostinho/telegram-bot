"""
P0 EXPIRAÇÃO: Teste RÁPIDO com 5 minutos (não 60)

Objetivo: Validar que a função funciona com Firestore real
antes de fazer deploy final.

TIMEOUT: 300 segundos (5 minutos)
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
import asyncio

try:
    import config.firebase_config
except Exception:
    pass

from services.firestore_client import get_db
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
)
from scheduler.notificacoes_scheduler import verificar_e_avisar_sessoes_expiradas


class TestSessaoExpiradaRapido:
    """Testes rápidos (5 minutos inatividade)."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        run_id = str(uuid.uuid4())[:8]
        self.tenant_id = f"p0_test_{run_id}"
        self.cliente_id = f"whatsapp:5511991382080_{run_id}"
        self.db = get_db()
        yield
        # Cleanup
        try:
            self.db.collection("Clientes").document(self.tenant_id).delete()
        except:
            pass

    async def _setup_tenant(self):
        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}",
            {
                "tipo_usuario": "dono",
                "nome": "Teste Dono",
            }
        )

    async def _setup_sessao_expirada_5min(self):
        """Criar sessão com 6 minutos de inatividade (para testar com timeout=5min)."""
        agora = datetime.now(timezone.utc)
        ts_atividade = agora - timedelta(minutes=6)  # 6 minutos atrás

        ctx = {
            "estado_fluxo": "agendando",
            "_last_client_activity": ts_atividade.isoformat(),
            "draft_agendamento": {
                "profissional": "Bruna",
                "data": "2026-10-16",
                "hora_inicio": "14:30",
            },
        }

        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}/Sessoes/{self.cliente_id}",
            ctx
        )

    @pytest.mark.asyncio
    async def test_sessao_expira_em_5min(self):
        """Sessão com 6 min de inatividade deve expirar (timeout=5min)."""
        await self._setup_tenant()
        await self._setup_sessao_expirada_5min()

        print(f"\n[TEST] Executando verificar_e_avisar_sessoes_expiradas()...")

        # Executar verificação
        await verificar_e_avisar_sessoes_expiradas()

        # Verificar resultado
        ctx_apos = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Sessoes/{self.cliente_id}"
        )

        print(f"[TEST] Contexto após: {ctx_apos}")

        assert ctx_apos is not None, "Sessão deve existir"
        assert "_aviso_expiracao_enviado" in ctx_apos, \
            f"Flag deve estar presente. Contexto: {ctx_apos.keys()}"

        print(f"[TEST] OK Flag presente: {ctx_apos.get('_aviso_expiracao_enviado')}")

    @pytest.mark.asyncio
    async def test_sessao_ativa_nao_expira(self):
        """Sessão com poucos minutos NÃO deve expirar."""
        await self._setup_tenant()

        agora = datetime.now(timezone.utc)
        ts_atividade = agora - timedelta(minutes=2)  # Apenas 2 minutos

        ctx = {
            "estado_fluxo": "agandando",
            "_last_client_activity": ts_atividade.isoformat(),
        }

        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}/Sessoes/{self.cliente_id}",
            ctx
        )

        # Executar
        await verificar_e_avisar_sessoes_expiradas()

        # Verificar que NÃO foi alterado
        ctx_apos = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Sessoes/{self.cliente_id}"
        )

        assert "_aviso_expiracao_enviado" not in ctx_apos, "Não deve ter aviso"
        print(f"[TEST] OK Sessao ativa preservada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
