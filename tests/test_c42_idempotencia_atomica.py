"""
C4.2 — Testes T9-T17: Idempotência Atômica com Firestore Transaction

Validação de máquina de estados com claim exclusivo
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.notificacoes_idempotencia_service import (
    tentar_claim_notificacao,
    confirmar_notificacao_processada,
    marcar_notificacao_erro,
    liberar_claim_abandonado,
)
from services.firestore_client import get_db
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path

FUSO_BR = pytz.timezone("America/Sao_Paulo")
TENANT = "c42_idempo_test"


class TestC42IdempotenciaAtomica:
    """Testes de idempotência com Firestore Transaction"""

    def setup_method(self):
        """Setup: criar tenant"""
        db = get_db()
        db.collection("Clientes").document(TENANT).set({
            "tipo_usuario": "dono",
            "nome": "Tenant Idempotência",
        })

    def teardown_method(self):
        """Cleanup"""
        db = get_db()
        try:
            db.collection("Clientes").document(TENANT).delete()
        except:
            pass

    # =========================================================
    # T9 — DUAS TRANSACTIONS CONCORRENTES: SÓ UMA OBTÉM CLAIM
    # =========================================================

    @pytest.mark.asyncio
    async def test_t9_duas_transactions_apenas_uma_claim(self):
        """T9: Duas instâncias tentam claim simultaneamente"""
        print("\n[T9] Duas transactions: apenas uma obtém claim")

        notif_id = f"t9_{uuid.uuid4().hex[:8]}"
        agora = datetime.now(FUSO_BR)
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"

        # Criar notificação
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
            "data_hora": (agora - timedelta(minutes=5)).isoformat(),
            "canal": "telegram",
            "mensagem": "[T9] Teste duas transactions",
        })

        # Duas instâncias tentam claim
        async def instancia_tenta_claim(inst_id):
            processo_id = f"proc_{inst_id}_{uuid.uuid4().hex[:4]}"
            sucesso, notif = await tentar_claim_notificacao(TENANT, notif_id, processo_id)
            return (inst_id, sucesso, processo_id)

        resultados = await asyncio.gather(
            instancia_tenta_claim(1),
            instancia_tenta_claim(2),
        )

        # Validar: apenas uma conseguiu
        claims_vencedores = [r for r in resultados if r[1] == True]
        assert len(claims_vencedores) == 1, f"[FAIL] {len(claims_vencedores)} claims vencedores, esperava 1"

        inst_vencedor = claims_vencedores[0][0]
        proc_vencedor = claims_vencedores[0][2]

        print(f"  [OK] Instância {inst_vencedor} ganhou o claim: {proc_vencedor}")

        # Validar documento
        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("status") == "processando", "[FAIL] Status não é processando"
        assert notif_final.get("processo_id") == proc_vencedor, "[FAIL] Processo_id incorreto"

        print("[PASS] T9: Claim exclusivo garantido")

    # =========================================================
    # T10 — DOCUMENTO EM "PROCESSANDO": SEGUNDA EXECUÇÃO NÃO ENVIA
    # =========================================================

    @pytest.mark.asyncio
    async def test_t10_documento_processando_recusa_claim(self):
        """T10: Documento já em 'processando' não permite novo claim"""
        print("\n[T10] Documento processando: recusa segundo claim")

        notif_id = f"t10_{uuid.uuid4().hex[:8]}"
        agora = datetime.now(FUSO_BR)
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"
        proc_1 = f"proc_1_{uuid.uuid4().hex[:4]}"

        # Criar e assumir notificação (primeira instância)
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
            "data_hora": (agora - timedelta(minutes=5)).isoformat(),
        })

        sucesso_1, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_1)
        assert sucesso_1, "[FAIL] Primeira instância não conseguiu claim"

        # Segunda instância tenta claim
        proc_2 = f"proc_2_{uuid.uuid4().hex[:4]}"
        sucesso_2, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_2)

        assert sucesso_2 == False, "[FAIL] Segunda instância conseguiu claim (não deveria)"

        # Validar que documento permanece com processo_id da primeira
        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("processo_id") == proc_1, "[FAIL] Processo_id foi alterado"

        print("[PASS] T10: Segundo claim foi recusado")

    # =========================================================
    # T11 — DOCUMENTO "AVISADO": NÃO PROCESSA
    # =========================================================

    @pytest.mark.asyncio
    async def test_t11_documento_avisado_recusa_claim(self):
        """T11: Documento já 'avisado' (processado) não permite novo claim"""
        print("\n[T11] Documento avisado: recusa reprocessamento")

        notif_id = f"t11_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"

        # Criar documento já processado
        await salvar_dado_em_path(path, {
            "status": "enviado",
            "avisado": True,
            "enviado_em": datetime.now(FUSO_BR).isoformat(),
        })

        # Tentar claim
        proc_id = f"proc_{uuid.uuid4().hex[:4]}"
        sucesso, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_id)

        assert sucesso == False, "[FAIL] Permitiu claim em documento já avisado"

        print("[PASS] T11: Reprocessamento foi bloqueado")

    # =========================================================
    # T12 — CLAIM EXPIRADO: RETRY PODE RECUPERAR
    # =========================================================

    @pytest.mark.asyncio
    async def test_t12_claim_expirado_permite_recuperacao(self):
        """T12: Se claim expirou, permite recuperação"""
        print("\n[T12] Claim expirado: recuperação permitida")

        notif_id = f"t12_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"

        # Criar documento com claim expirado
        agora = datetime.now(FUSO_BR)
        tempo_expirado = (agora - timedelta(minutes=10)).isoformat()

        await salvar_dado_em_path(path, {
            "status": "processando",
            "avisado": False,
            "processo_id": "proc_morto",
            "processando_em": tempo_expirado,
        })

        # Tentar recuperar com novo processo
        proc_novo = f"proc_novo_{uuid.uuid4().hex[:4]}"
        sucesso, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_novo)

        assert sucesso == True, "[FAIL] Não permitiu recuperação de claim expirado"

        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("processo_id") == proc_novo, "[FAIL] Processo_id não foi atualizado"

        print("[PASS] T12: Claim expirado foi recuperado")

    # =========================================================
    # T13 — CLAIM NÃO EXPIRADO: RETRY NÃO ASSUME
    # =========================================================

    @pytest.mark.asyncio
    async def test_t13_claim_valido_recusa_retry(self):
        """T13: Se claim ainda é válido, retry não consegue"""
        print("\n[T13] Claim válido: retry recusado")

        notif_id = f"t13_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"

        agora = datetime.now(FUSO_BR)
        tempo_recente = (agora - timedelta(seconds=30)).isoformat()

        # Documento com claim recente
        await salvar_dado_em_path(path, {
            "status": "processando",
            "avisado": False,
            "processo_id": "proc_ativo",
            "processando_em": tempo_recente,
        })

        # Tentar recuperar (não deve conseguir)
        proc_novo = f"proc_novo_{uuid.uuid4().hex[:4]}"
        sucesso, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_novo)

        assert sucesso == False, "[FAIL] Permitiu sobrescrever claim válido"

        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("processo_id") == "proc_ativo", "[FAIL] Processo_id foi alterado"

        print("[PASS] T13: Claim válido não foi sobrescrito")

    # =========================================================
    # T14 — ERRO ANTES DO ENVIO: RECUPERÁVEL
    # =========================================================

    @pytest.mark.asyncio
    async def test_t14_erro_permite_retry(self):
        """T14: Erro antes do envio deixa estado recuperável"""
        print("\n[T14] Erro: estado permite retry")

        notif_id = f"t14_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"
        proc_id = f"proc_{uuid.uuid4().hex[:4]}"

        # Setup: criar e assumir
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
        })

        sucesso_claim, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_id)
        assert sucesso_claim, "[FAIL] Não conseguiu claim"

        # Marcar erro (sem confirmar)
        await marcar_notificacao_erro(TENANT, notif_id, proc_id, "Erro simulado")

        # Validar estado: avisado=False, status=erro
        notif_erro = await buscar_dado_em_path(path)
        assert notif_erro.get("avisado") == False, "[FAIL] Marcou como avisado"
        assert notif_erro.get("status") == "erro", "[FAIL] Status não é erro"
        assert notif_erro.get("processo_id") is None, "[FAIL] Claim não foi liberado"

        # Retry: consegue novo claim
        proc_novo = f"proc_retry_{uuid.uuid4().hex[:4]}"
        sucesso_retry, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_novo)

        assert sucesso_retry == True, "[FAIL] Retry não conseguiu novo claim"

        print("[PASS] T14: Erro permite retry")

    # =========================================================
    # T15 — ERRO APÓS ENVIO: CONFIRMAR MESMO ASSIM
    # =========================================================

    @pytest.mark.asyncio
    async def test_t15_erro_apos_envio_pode_confirmar(self):
        """T15: Se envio bem-sucedido, confirmar mesmo se houve erro depois"""
        print("\n[T15] Erro pós-envio: confirmação possível")

        notif_id = f"t15_{uuid.uuid4().hex[:8]}"
        path = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_id}"
        proc_id = f"proc_{uuid.uuid4().hex[:4]}"

        # Setup
        await salvar_dado_em_path(path, {
            "status": "pendente",
            "avisado": False,
        })

        sucesso_claim, _ = await tentar_claim_notificacao(TENANT, notif_id, proc_id)
        assert sucesso_claim, "[FAIL] Não conseguiu claim"

        # Simular: envio bem-sucedido, mas erro depois
        # Estado atual: processando

        # Confirmar mesmo assim
        sucesso_confirm = await confirmar_notificacao_processada(TENANT, notif_id, proc_id)
        assert sucesso_confirm == True, "[FAIL] Não permitiu confirmação"

        notif_final = await buscar_dado_em_path(path)
        assert notif_final.get("avisado") == True, "[FAIL] Não marcou como avisado"
        assert notif_final.get("status") == "enviado", "[FAIL] Status não é enviado"

        print("[PASS] T15: Confirmação após erro funcionou")

    # =========================================================
    # T16 — DUAS NOTIFICAÇÕES DIFERENTES DO MESMO TENANT
    # =========================================================

    @pytest.mark.asyncio
    async def test_t16_notificacoes_diferentes_processam_independentemente(self):
        """T16: Duas notificações diferentes não interferem"""
        print("\n[T16] Notificações diferentes: processamento independente")

        notif_a = f"t16_a_{uuid.uuid4().hex[:4]}"
        notif_b = f"t16_b_{uuid.uuid4().hex[:4]}"
        path_a = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_a}"
        path_b = f"Clientes/{TENANT}/NotificacoesAgendadas/{notif_b}"

        # Criar ambas
        for path in [path_a, path_b]:
            await salvar_dado_em_path(path, {
                "status": "pendente",
                "avisado": False,
            })

        # Processar A
        proc_a = f"proc_a_{uuid.uuid4().hex[:4]}"
        sucesso_a, _ = await tentar_claim_notificacao(TENANT, notif_a, proc_a)
        assert sucesso_a, "[FAIL] Não conseguiu claim de A"

        # Processar B
        proc_b = f"proc_b_{uuid.uuid4().hex[:4]}"
        sucesso_b, _ = await tentar_claim_notificacao(TENANT, notif_b, proc_b)
        assert sucesso_b, "[FAIL] Não conseguiu claim de B"

        # Ambas devem estar processando
        notif_a_final = await buscar_dado_em_path(path_a)
        notif_b_final = await buscar_dado_em_path(path_b)

        assert notif_a_final.get("processo_id") == proc_a, "[FAIL] A: processo_id incorreto"
        assert notif_b_final.get("processo_id") == proc_b, "[FAIL] B: processo_id incorreto"

        print("[PASS] T16: Notificações diferentes processadas independentemente")

    # =========================================================
    # T17 — NOTIFICAÇÕES IGUAIS EM TENANTS DIFERENTES
    # =========================================================

    @pytest.mark.asyncio
    async def test_t17_notificacoes_iguais_tenants_diferentes_independentes(self):
        """T17: Mesma notificação em tenants diferentes são isoladas"""
        print("\n[T17] Notificações iguais em tenants: isolamento")

        tenant_a = f"t17_tenant_a_{uuid.uuid4().hex[:4]}"
        tenant_b = f"t17_tenant_b_{uuid.uuid4().hex[:4]}"
        notif_id = "notif_comum"

        # Criar tenants
        db = get_db()
        for tenant in [tenant_a, tenant_b]:
            db.collection("Clientes").document(tenant).set({"tipo_usuario": "dono"})

        # Criar notificações IGUAIS em ambos tenants
        path_a = f"Clientes/{tenant_a}/NotificacoesAgendadas/{notif_id}"
        path_b = f"Clientes/{tenant_b}/NotificacoesAgendadas/{notif_id}"

        for path in [path_a, path_b]:
            await salvar_dado_em_path(path, {
                "status": "pendente",
                "avisado": False,
                "mensagem": "Notificação idêntica",
            })

        # Processar em tenant A
        proc_a = f"proc_a_{uuid.uuid4().hex[:4]}"
        sucesso_a, _ = await tentar_claim_notificacao(tenant_a, notif_id, proc_a)
        assert sucesso_a, "[FAIL] A: não conseguiu claim"

        # Processar em tenant B (deve independente)
        proc_b = f"proc_b_{uuid.uuid4().hex[:4]}"
        sucesso_b, _ = await tentar_claim_notificacao(tenant_b, notif_id, proc_b)
        assert sucesso_b, "[FAIL] B: não conseguiu claim"

        # Ambas devem ter seus próprios claims
        notif_a = await buscar_dado_em_path(path_a)
        notif_b = await buscar_dado_em_path(path_b)

        assert notif_a.get("processo_id") == proc_a, "[FAIL] A: processo_id incorreto"
        assert notif_b.get("processo_id") == proc_b, "[FAIL] B: processo_id incorreto"

        print("[PASS] T17: Isolamento de tenants confirmado")

        # Cleanup
        for tenant in [tenant_a, tenant_b]:
            try:
                db.collection("Clientes").document(tenant).delete()
            except:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
