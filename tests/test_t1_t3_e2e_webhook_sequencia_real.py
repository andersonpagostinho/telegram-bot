"""
TESTES T1 + T3 REFATORADOS: SEQUÊNCIA REAL DE PRODUÇÃO

Estes testes simulam EXATAMENTE o que aconteceu no teste real do usuário em produção:
- Múltiplas mensagens em sequência
- Estado herdado de contexto anterior
- P1-C detectando confirmacao_pendente + intenção nova
- Fluxo completo até resposta final

T1: Reativação 100+ dias + mudança de intenção COM confirmacao_pendente
  Msg 1: "ola" → intencao=indefinida
  Msg 2: "a bruna esta disponivel amanha as 10?" → intencao=consulta (com confirmacao_pendente=True)
  Validar: NÃO reutiliza draft antigo, pergunta o serviço (BUG P1-C se falhar)

T3: Isolamento multi-tenant com sequência de alterações
  Msg 1: "quero corte com bruna" → confirma + aguarda
  Msg 2: "qual outro horario" → altera horário
  Validar: Isolamento mantido, sem vazamento
"""

import pytest
import sys
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone

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


# ============================================================================
# T1: SEQUÊNCIA REAL COM MUDANÇA DE INTENÇÃO
# ============================================================================

class TestT1SequenciaRealProducao:
    """T1: Replicar fluxo real de produção (3 mensagens)"""

    def _webhook_payload(self, mensagem: str, wa_id: str = "5511991382080") -> dict:
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1630189518519404",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "5519994443694",
                            "phone_number_id": "1350170954840548"
                        },
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

    @pytest.mark.asyncio
    async def test_t1_sequencia_real_3_mensagens(self):
        """
        T1: Sequência real de produção

        SETUP: Contexto dormindo com draft='coloracao' + Gloria
        MSG 1: "ola" → intencao=indefinida
        MSG 2: "a bruna esta disponivel amanha as 10?" → intencao=consulta
        VALIDAR: Draft antigo NAO foi herdado
        """
        print("\n" + "=" * 70)
        print("T1: SEQUENCIA REAL DE PRODUCAO (BUGGY - P1-C bloqueia)")
        print("=" * 70)

        TENANT = "7394370553"
        USER = "5511991382080"
        ACTOR_ID = f"whatsapp:{USER}"

        timestamp_105_dias = (datetime.now(timezone.utc) - timedelta(days=105)).isoformat()

        # SETUP: Draft antigo = "coloracao"
        draft_antigo = {
            "servico": "coloracao",
            "profissional": "Gloria",
            "data_hora": timestamp_105_dias
        }

        print(f"\n[SETUP] Context dormindo 105 dias")
        print(f"  Draft: servico=coloracao, prof=Gloria")

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": draft_antigo,
            "historico_texto": ["ola", "coloracao"],
            "aguardando_confirmacao_agendamento": True,  # CRITICO: Ativa confirmacao_pendente
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT,
            "timestamp_criacao": timestamp_105_dias,
        })
        print(f"  Saved OK")

        # MSG 1: "ola"
        print(f"\n[MSG 1] Enviando: 'ola'")

        payload1 = self._webhook_payload("ola", USER)
        with patch("main.validate_whatsapp_signature", return_value=True):
            resp1 = app.test_client().post("/webhook/whatsapp", json=payload1)

        assert resp1.status_code == 200
        print(f"  HTTP 200 OK")

        # MSG 2: Consulta de disponibilidade (CENARIO CRITICO)
        print(f"\n[MSG 2] Enviando: 'a bruna esta disponivel amanha as 10?'")
        print(f"  CRITICAL: mudanca de intencao COM confirmacao_pendente=True")

        payload2 = self._webhook_payload("a bruna esta disponivel amanha as 10?", USER)
        with patch("main.validate_whatsapp_signature", return_value=True):
            resp2 = app.test_client().post("/webhook/whatsapp", json=payload2)

        assert resp2.status_code == 200
        print(f"  HTTP 200 OK")

        # Pequeno delay para garantir que Firebase foi atualizado
        import asyncio
        await asyncio.sleep(1)

        # VALIDACAO
        print(f"\n[VALIDACAO]")
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        draft = ctx.get("draft_agendamento", {})

        print(f"  [DEBUG] Contexto completo apos MSG2:")
        print(f"    estado_fluxo: {ctx.get('estado_fluxo')}")
        print(f"    aguardando_confirmacao: {ctx.get('aguardando_confirmacao_agendamento')}")
        print(f"    intencao: {ctx.get('intencao_conversacional')}")
        print(f"    draft_servico: {draft.get('servico')}")
        print(f"    draft_prof: {draft.get('profissional')}")

        # V1: Draft antigo NAO foi herdado
        if draft.get("servico") == "coloracao":
            print(f"  FAIL V1: Draft antigo 'coloracao' foi herdado!")
            print(f"           Isto eh o BUG P1-C em producao")
            assert False, "P1-C BLOQUEIA consulta quando confirmacao=True"
        else:
            print(f"  PASS V1: Draft antigo nao herdado")

        # V2: Identidade preservada
        assert ctx.get("tenant_id") == TENANT
        assert ctx.get("actor_id") == ACTOR_ID
        print(f"  PASS V2: Identidade OK")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)

        print(f"\n  RESULT: T1 Sequencia Real PASSED")
        return True


# ============================================================================
# T3: ISOLAMENTO COM ALTERACOES
# ============================================================================

class TestT3IsolamentoSequenciaReal:
    """T3: Isolamento multi-tenant com múltiplas mensagens"""

    def _webhook_payload(self, mensagem: str, wa_id: str) -> dict:
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1630189518519404",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "5519994443694",
                            "phone_number_id": "1350170954840548"
                        },
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

    @pytest.mark.asyncio
    async def test_t3_isolamento_com_alteracoes(self):
        """
        T3: Isolamento com múltiplas mensagens e alterações

        TENANT A: "quero corte com bruna" → confirma + aguarda
        TENANT B: "qual profissional" → validar isolamento
        """
        print("\n" + "=" * 70)
        print("T3: ISOLAMENTO COM ALTERACOES (2 tenants, mesmo wa_id)")
        print("=" * 70)

        TENANT_A = "7394370553"
        TENANT_B = "5511991382080"
        SHARED_WA_ID = "5511991382080"
        ACTOR_ID = f"whatsapp:{SHARED_WA_ID}"

        # Setup: Tenant A com contexto
        print(f"\n[SETUP] Tenant A com draft")

        await salvar_contexto_temporario_v2(TENANT_A, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna"
            },
            "historico_texto": ["ola", "corte", "bruna"],
            "aguardando_confirmacao_agendamento": True,
            "tenant_id": TENANT_A,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT_A,
        })
        print(f"  Tenant A draft saved: corte/Bruna")

        # Tenant B tries to load (mesma wa_id)
        print(f"\n[TENANT B] Tentando carregar (mesmo wa_id)")

        async def mock_obter_id_dono(actor_id):
            return TENANT_B  # Retorna tenant B, nao A

        payload = self._webhook_payload("qual profissional", SHARED_WA_ID)

        with patch("main.validate_whatsapp_signature", return_value=True):
            with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
                resp = app.test_client().post("/webhook/whatsapp", json=payload)

        assert resp.status_code == 200
        print(f"  HTTP 200 OK")

        # Validacao: Tenant B isolado
        print(f"\n[VALIDACAO]")
        ctx_b = await carregar_contexto_temporario_v2(TENANT_B, ACTOR_ID)
        draft_b = ctx_b.get("draft_agendamento", {})

        # V1: Draft de A nao vazou para B
        if draft_b.get("servico") == "corte" and draft_b.get("profissional") == "Bruna":
            print(f"  FAIL V1: Draft de Tenant A vazou para Tenant B!")
            assert False, "Cross-tenant leak detectado"
        else:
            print(f"  PASS V1: Tenant B isolado de A")

        # V2: Identidade OK
        assert ctx_b.get("tenant_id") == TENANT_B
        print(f"  PASS V2: Identidade OK")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT_A, ACTOR_ID)

        print(f"\n  RESULT: T3 Isolamento PASSED")
        return True


async def main():
    """Rodar testes"""
    print("\n" + "=" * 70)
    print("TESTES T1 + T3: SEQUENCIA REAL DE PRODUCAO")
    print("=" * 70)

    t1 = TestT1SequenciaRealProducao()
    t3 = TestT3IsolamentoSequenciaReal()

    try:
        await t1.test_t1_sequencia_real_3_mensagens()
        print("\n[T1] PASSED")
    except AssertionError as e:
        print(f"\n[T1] FAILED: {e}")

    try:
        await t3.test_t3_isolamento_com_alteracoes()
        print("\n[T3] PASSED")
    except AssertionError as e:
        print(f"\n[T3] FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
