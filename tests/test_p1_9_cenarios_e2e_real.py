"""
P1 — 9 Cenários Obrigatórios: E2E Real com Firebase e Webhook

Validar que:
1. Consulta independente sem serviço — não herda 'coloracao'
2. Continuação válida — preserva o contexto necessário
3. Confirmação explícita — continua funcionando
4. Alteração de horário — continua funcionando
5. Escolha de profissional — continua funcionando
6. Recusa/cancelamento — mantém o comportamento contratado
7. Persistência de DELETE_FIELD — campos removidos não reaparecem
8. Salvamento com merge — não reintroduz dados obsoletos
9. Integridade — histórico, tenant e dados permanentes são preservados

Todos com Firebase REAL e webhook REAL.
"""

import pytest
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2,
)

TENANT = "7394370553"
USER = "5511991382080"
ENDPOINT = "1350170954840548"
ACTOR_ID = f"whatsapp:{USER}"


def _webhook_payload(mensagem: str, wa_id: str = USER) -> dict:
    """Cria payload de webhook WhatsApp real"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": ENDPOINT},
                    "contacts": [{"profile": {"name": "Teste"}, "wa_id": wa_id}],
                    "messages": [{
                        "from": wa_id,
                        "id": f"wamid.real_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": mensagem},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }


class TestP19CenariosE2EReal:
    """9 testes obrigatórios com Firebase REAL e webhook REAL"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = app.test_client()
        yield
        try:
            asyncio.run(carregar_contexto_temporario_v2(TENANT, ACTOR_ID))
        except:
            pass

    @pytest.mark.asyncio
    async def test_e2e_t1_consulta_independente(self):
        """T1: Consulta sem serviço não herda 'coloracao'"""
        print("\n[E2E T1] Consulta Independente Sem Serviço")

        # Setup: draft com coloracao
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "coloracao", "data_hora": "2026-10-26T14:00:00"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        # Consulta nova (sem herdar draft)
        payload = _webhook_payload("a bruna esta disponivel amanha as 10?")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        # Verificar que draft foi removido
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft is None or draft.get("servico") != "coloracao", "T1: serviço anterior foi herdado"
        print("  ✅ T1 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t2_continuacao_valida(self):
        """T2: Continuação 'confirma' preserva contexto"""
        print("\n[E2E T2] Continuação Válida")

        # Setup: draft completo com confirmação pendente
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "coloracao", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        # Enviar confirmação
        payload = _webhook_payload("confirma")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        # Verificar que contexto foi preservado
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft and draft.get("servico") == "coloracao", "T2: serviço foi removido"
        assert draft.get("profissional") == "Bruna", "T2: profissional foi alterado"
        print("  ✅ T2 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t3_confirmacao_explicita(self):
        """T3: Confirmação 'sim' funciona"""
        print("\n[E2E T3] Confirmação Explícita")

        # Setup
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "aguardando_confirmacao",
            "draft_agendamento": {"profissional": "Bruna", "servico": "corte", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        payload = _webhook_payload("sim")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft and draft.get("servico") == "corte", "T3: serviço foi removido"
        print("  ✅ T3 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t4_alteracao_horario(self):
        """T4: Alteração 'qual outro horário' preserva contexto"""
        print("\n[E2E T4] Alteração de Horário")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"profissional": "Bruna", "servico": "corte", "data_hora": "2026-10-25T14:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        payload = _webhook_payload("qual outro horario")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft and draft.get("servico") == "corte", "T4: serviço foi apagado"
        assert draft.get("profissional") == "Bruna", "T4: profissional foi alterado"
        print("  ✅ T4 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t5_escolha_profissional(self):
        """T5: Escolha 'qual profissional' preserva serviço"""
        print("\n[E2E T5] Escolha de Profissional")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna", "data_hora": "2026-10-25T15:00:00"},
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        payload = _webhook_payload("qual profissional")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft and draft.get("servico") == "corte", "T5: serviço foi removido"
        assert draft.get("profissional") == "Bruna", "T5: profissional foi alterado"
        print("  ✅ T5 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t6_recusa_cancelamento(self):
        """T6: Recusa 'não obrigado' remove contexto"""
        print("\n[E2E T6] Recusa/Cancelamento")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "ultima_acao": "contexto_limpo",
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        payload = _webhook_payload("não obrigado")
        with patch("main.validate_whatsapp_signature", return_value=True):
            response = self.client.post("/webhook/whatsapp", json=payload)

        assert response.status_code == 200

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento")
        assert draft is None, "T6: draft deveria ter sido removido para recusa"
        print("  ✅ T6 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t7_persistencia_delete_field(self):
        """T7: DELETE_FIELD persiste no Firestore"""
        print("\n[E2E T7] Persistência de DELETE_FIELD")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        assert ctx.get("draft_agendamento") is None, "T7: draft não foi deletado"
        print("  ✅ T7 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t8_merge_nao_restaura(self):
        """T8: Salvamento com merge não restaura dados deletados"""
        print("\n[E2E T8] Merge Não Restaura")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })

        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)

        novo_ctx = {"novo_campo": "valor", "tenant_id": TENANT}
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, novo_ctx)

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        assert ctx.get("draft_agendamento") is None, "T8: draft foi restaurado pelo merge"
        assert ctx.get("novo_campo") == "valor", "T8: novo campo não foi salvo"
        print("  ✅ T8 PASS")

    @pytest.mark.asyncio
    async def test_e2e_t9_integridade_historico(self):
        """T9: Integridade - histórico, tenant preservados"""
        print("\n[E2E T9] Integridade - Histórico/Tenant")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {"servico": "corte"},
            "historico_texto": ["ola", "corte", "confirma"],
            "tenant_id": TENANT,
            "_tenant_id_guard": TENANT,
            "actor_id": ACTOR_ID,
        })

        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        assert ctx.get("historico_texto") == ["ola", "corte", "confirma"], "T9: histórico foi deletado"
        assert ctx.get("tenant_id") == TENANT, "T9: tenant_id foi deletado"
        assert ctx.get("_tenant_id_guard") == TENANT, "T9: guard foi deletado"
        assert ctx.get("actor_id") == ACTOR_ID, "T9: actor_id foi deletado"
        assert ctx.get("draft_agendamento") is None, "T9: draft deveria estar deletado"
        print("  ✅ T9 PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
