"""
TEST BLOCKER B: Timeout de Sessão — FIX

Objetivo: Verificar que _aviso_expiracao_enviado é setada quando sessão expira.

[FIX-BLOQ-B] O timeout de produção é 3600 segundos (60 minutos).
Este teste simula que "agora" é 61 minutos depois da última atividade,
forçando a condição de expiração.
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


class TestSessaoTimeoutFix:
    """Testes para bloqueador B: timeout de sessão."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        run_id = str(uuid.uuid4())[:8]
        self.tenant_id = f"p0_test_{run_id}"
        self.cliente_id = f"whatsapp:5511991382080_{run_id}"
        self.db = get_db()
        yield
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

    async def _setup_sessao_expirada(self):
        """Criar sessão com 61 minutos de inatividade (vai expirar com timeout=60min)."""
        agora = datetime.now(timezone.utc)
        ts_atividade = agora - timedelta(minutes=61)  # 61 minutos atrás

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
    async def test_timeout_flag_setada_sessao_expirada(self):
        """[FIX-BLOQ-B] Flag _aviso_expiracao_enviado deve ser setada quando sessão expira."""
        await self._setup_tenant()
        await self._setup_sessao_expirada()

        print(f"\n[TEST] Executando verificar_e_avisar_sessoes_expiradas()...")

        # Executar verificação (timeout de 60 minutos em produção)
        await verificar_e_avisar_sessoes_expiradas()

        # Verificar resultado
        ctx_apos = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Sessoes/{self.cliente_id}"
        )

        print(f"[TEST] Contexto após: {ctx_apos.keys() if ctx_apos else 'None'}")

        # VALIDAÇÕES
        assert ctx_apos is not None, "Sessão deve existir após expiração"
        assert "_aviso_expiracao_enviado" in ctx_apos, \
            f"Flag deve estar presente. Contexto: {list(ctx_apos.keys())}"
        assert ctx_apos["_aviso_expiracao_enviado"], "Flag deve ter valor timestamp"
        assert "_aviso_sucesso" in ctx_apos, "Campo _aviso_sucesso deve ser setado"

        print(f"[TEST] ✅ PASS: Flag presente = {ctx_apos.get('_aviso_expiracao_enviado')}")

    @pytest.mark.asyncio
    async def test_timeout_sessao_ativa_nao_expira(self):
        """Sessão com poucos minutos NÃO deve expirar (timeout=60min)."""
        await self._setup_tenant()

        agora = datetime.now(timezone.utc)
        ts_atividade = agora - timedelta(minutes=2)  # Apenas 2 minutos

        ctx = {
            "estado_fluxo": "agendando",
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
            f"Clientes/{self.tenant_id}/Sessões/{self.cliente_id}"
        )

        if ctx_apos:
            assert "_aviso_expiracao_enviado" not in ctx_apos, \
                "Sessão ativa NÃO deve ter flag de expiração"

        print(f"[TEST] ✅ PASS: Sessão ativa não expirou")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
