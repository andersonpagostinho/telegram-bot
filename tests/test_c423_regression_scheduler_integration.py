"""
C4.2.3 — Testes de Regressão do Scheduler Após Integração de Idempotência

Objetivo: Validar que a integração C4.2.2 não quebra fluxos existentes
e que claim/confirmar/erro funcionam corretamente no scheduler.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    atualizar_dado_em_path,
)
from services.firestore_client import get_db
import pytz

FUSO_BR = pytz.timezone("America/Sao_Paulo")
TENANT_TEST = f"c423_test_{uuid.uuid4().hex[:8]}"


class TestC423RegressionScheduler:
    """Testes de regressão do scheduler após integração C4.2.2"""

    def setup_method(self):
        """Criar tenant de teste"""
        db = get_db()
        db.collection("Clientes").document(TENANT_TEST).set({
            "tipo_usuario": "dono",
            "nome": "Tenant C4.2.3",
        })

    def teardown_method(self):
        """Limpar tenant de teste"""
        db = get_db()
        try:
            db.collection("Clientes").document(TENANT_TEST).delete()
        except:
            pass

    # =========================================================
    # T1 — PENDENTE → CLAIM → ENVIO → AVISADO
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t1_fluxo_completo(self):
        """T1: Notificação segue fluxo completo"""
        print("\n[C4.2.3-T1] Fluxo completo: PENDENTE → CLAIM → ENVIO → AVISADO")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
            confirmar_notificacao_processada,
        )

        notif_id = f"t1_{uuid.uuid4().hex[:8]}"
        processo_id = f"proc_{uuid.uuid4().hex[:8]}"
        agora = datetime.now(FUSO_BR)
        path = f"Clientes/{TENANT_TEST}/NotificacoesAgendadas/{notif_id}"

        # Criar notificação
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
            "data_hora": (agora - timedelta(minutes=5)).isoformat(),
            "canal": "telegram",
            "mensagem": "[C4.2.3-T1] Teste fluxo",
        })

        # Tentar claim
        sucesso_claim, _ = await tentar_claim_notificacao(
            TENANT_TEST, notif_id, processo_id
        )
        assert sucesso_claim, "[FAIL] Não conseguiu claim"

        # Verificar estado após claim
        notif_claim = await buscar_dado_em_path(path)
        assert notif_claim.get("status") == "processando"
        assert notif_claim.get("processo_id") == processo_id

        # Confirmar processamento
        sucesso_confirm = await confirmar_notificacao_processada(
            TENANT_TEST, notif_id, processo_id
        )
        assert sucesso_confirm, "[FAIL] Não conseguiu confirmar"

        # Verificar estado final
        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("avisado") == True
        assert notif_final.get("status") == "enviado"

        print("[PASS] T1: Fluxo completo OK")

    # =========================================================
    # T2 — CONCORRÊNCIA: SEGUNDO PROCESSO SKIPA
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t2_segundo_processo_skipa(self):
        """T2: Segundo processo concorrente skipa"""
        print("\n[C4.2.3-T2] Concorrência: segundo processo skipa")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
        )

        notif_id = f"t2_{uuid.uuid4().hex[:8]}"
        processo1 = f"proc1_{uuid.uuid4().hex[:4]}"
        processo2 = f"proc2_{uuid.uuid4().hex[:4]}"
        agora = datetime.now(FUSO_BR)
        path = f"Clientes/{TENANT_TEST}/NotificacoesAgendadas/{notif_id}"

        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
            "data_hora": (agora - timedelta(minutes=5)).isoformat(),
        })

        # Ambas tentam claim
        async def tenta_claim(proc_id):
            sucesso, _ = await tentar_claim_notificacao(
                TENANT_TEST, notif_id, proc_id
            )
            return sucesso

        resultado1, resultado2 = await asyncio.gather(
            tenta_claim(processo1),
            tenta_claim(processo2),
        )

        # Apenas uma consegue
        assert (resultado1 and not resultado2) or (not resultado1 and resultado2)
        print("[PASS] T2: Concorrência bloqueada")

    # =========================================================
    # T3 — AVISADO NÃO REPROCESSA
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t3_avisado_nao_reprocessa(self):
        """T3: Documento avisado não é reprocessado"""
        print("\n[C4.2.3-T3] Avisado não reprocessa")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
        )

        notif_id = f"t3_{uuid.uuid4().hex[:8]}"
        processo_id = f"proc_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT_TEST}/NotificacoesAgendadas/{notif_id}"

        # Criar como avisado
        await salvar_dado_em_path(path, {
            "status": "enviado",
            "avisado": True,
            "enviado_em": datetime.now(FUSO_BR).isoformat(),
        })

        # Tentar claim deve falhar
        sucesso, _ = await tentar_claim_notificacao(
            TENANT_TEST, notif_id, processo_id
        )
        assert not sucesso, "[FAIL] Permitiu claim de avisado"

        print("[PASS] T3: Avisado bloqueado")

    # =========================================================
    # T4 — ERRO NÃO CONFIRMA AVISADO
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t4_erro_nao_confirma_avisado(self):
        """T4: Erro não marca como AVISADO"""
        print("\n[C4.2.3-T4] Erro não marca AVISADO")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
            marcar_notificacao_erro,
        )

        notif_id = f"t4_{uuid.uuid4().hex[:8]}"
        processo_id = f"proc_{uuid.uuid4().hex[:8]}"
        agora = datetime.now(FUSO_BR)
        path = f"Clientes/{TENANT_TEST}/NotificacoesAgendadas/{notif_id}"

        # Setup
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
        })

        # Claim
        sucesso_claim, _ = await tentar_claim_notificacao(
            TENANT_TEST, notif_id, processo_id
        )
        assert sucesso_claim

        # Marcar erro
        await marcar_notificacao_erro(
            TENANT_TEST, notif_id, processo_id, "Erro simulado"
        )

        # Validar: NÃO avisado
        notif = await buscar_dado_em_path(path)
        assert notif.get("avisado") == False, "[FAIL] Avisado foi marcado"
        assert notif.get("status") == "erro"
        assert notif.get("processo_id") is None  # Claim liberado

        print("[PASS] T4: Erro não confirma")

    # =========================================================
    # T5 — CLAIM EXPIRA EM 60 SEGUNDOS
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t5_claim_expira_60s(self):
        """T5: Claim expirado em 60+ segundos"""
        print("\n[C4.2.3-T5] Claim expira em 60 segundos")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
        )

        notif_id = f"t5_{uuid.uuid4().hex[:8]}"
        processo_novo = f"proc_new_{uuid.uuid4().hex[:4]}"
        path = f"Clientes/{TENANT_TEST}/NotificacoesAgendadas/{notif_id}"

        # Criar com claim expirado (>60s)
        agora = datetime.now(FUSO_BR)
        tempo_expirado = (agora - timedelta(seconds=70)).isoformat()

        await salvar_dado_em_path(path, {
            "status": "processando",
            "avisado": False,
            "processo_id": "proc_morto",
            "processando_em": tempo_expirado,
        })

        # Novo processo deve conseguir
        sucesso, _ = await tentar_claim_notificacao(
            TENANT_TEST, notif_id, processo_novo
        )
        assert sucesso, "[FAIL] Não permitiu recuperação"

        notif = await buscar_dado_em_path(path)
        assert notif.get("processo_id") == processo_novo

        print("[PASS] T5: Timeout 60s funciona")

    # =========================================================
    # T6 — ISOLAMENTO ENTRE TENANTS
    # =========================================================

    @pytest.mark.asyncio
    async def test_c423_t6_isolamento_tenant(self):
        """T6: Tenants são isolados"""
        print("\n[C4.2.3-T6] Isolamento entre tenants")

        from services.notificacoes_idempotencia_service import (
            tentar_claim_notificacao,
        )

        tenant_a = f"a_{uuid.uuid4().hex[:4]}"
        tenant_b = f"b_{uuid.uuid4().hex[:4]}"
        notif_id = "notif_compartilhado"
        proc_a = f"proc_a_{uuid.uuid4().hex[:4]}"
        proc_b = f"proc_b_{uuid.uuid4().hex[:4]}"

        db = get_db()
        for tenant in [tenant_a, tenant_b]:
            db.collection("Clientes").document(tenant).set({"tipo_usuario": "dono"})

        # Criar mesma notif_id em ambos tenants
        for tenant in [tenant_a, tenant_b]:
            path = f"Clientes/{tenant}/NotificacoesAgendadas/{notif_id}"
            await salvar_dado_em_path(path, {
                "status": "pendente",
                "avisado": False,
            })

        # Ambos conseguem claim (isolamento)
        sucesso_a, _ = await tentar_claim_notificacao(tenant_a, notif_id, proc_a)
        sucesso_b, _ = await tentar_claim_notificacao(tenant_b, notif_id, proc_b)

        assert sucesso_a, "[FAIL] Tenant A falhou"
        assert sucesso_b, "[FAIL] Tenant B falhou"

        # Cleanup
        for tenant in [tenant_a, tenant_b]:
            try:
                db.collection("Clientes").document(tenant).delete()
            except:
                pass

        print("[PASS] T6: Isolamento garantido")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
