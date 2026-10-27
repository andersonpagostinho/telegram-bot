"""
Teste focado no cenário de conflito que deu erro em produção:
- MSG: "corte" (ajuste_incremental)
- Profissional: Bruna
- Horário: 2026-10-27 10:00 (JÁ OCUPADO)
- Resultado esperado: Sem erro .strip() em lista
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2, limpar_contexto_agendamento_v2


class TestConflitoDraftPersistencia:
    """Teste de cenário: profissional já ocupado no horário solicitado"""

    def _webhook_payload(self, mensagem: str, wa_id: str = "5511991382080") -> dict:
        import time
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
    async def test_conflito_bruna_27_outubro_10h(self):
        """
        Cenário: Draft já existe com data_hora 2026-10-27 10:00 (ocupado)
        MSG: "corte" → ajuste_incremental
        ESPERADO: Sugerir horários alternativos SEM erro .strip()
        """
        print("\n" + "=" * 70)
        print("TESTE CONFLITO: Bruna 27/outubro 10h (JÁ OCUPADA)")
        print("=" * 70)

        TENANT = "7394370553"
        USER = "5511991382080"
        ACTOR_ID = f"whatsapp:{USER}"

        # SETUP: Draft anterior com horário que já tem evento
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "aguardando_servico",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-10-27T10:00:00"
            },
            "historico_texto": ["a bruna esta disponivel amanha as 10?"],
            "profissional_escolhido": "Bruna",
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT,
            "intencao_conversacional": "consulta_disponibilidade_aberta"
        })
        print(f"[SETUP] Context salvo com draft: Bruna 2026-10-27 10:00")

        # MSG: "corte"
        print(f"\n[MSG] Enviando: 'corte'")
        payload = self._webhook_payload("corte", USER)

        with patch("main.validate_whatsapp_signature", return_value=True):
            try:
                resp = app.test_client().post("/webhook/whatsapp", json=payload)
                print(f"[RESPOSTA] HTTP {resp.status_code}")
                assert resp.status_code == 200, f"Erro HTTP: {resp.status_code}"
            except Exception as e:
                print(f"[ERRO] {e}")
                raise

        # VALIDACAO
        print(f"\n[VALIDACAO]")
        import asyncio
        await asyncio.sleep(1)

        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        print(f"  estado_fluxo: {ctx.get('estado_fluxo')}")
        print(f"  modo_escolha_horario: {ctx.get('modo_escolha_horario')}")
        print(f"  horarios_sugeridos: {ctx.get('horarios_sugeridos')}")

        # Validacao: Deve estar em aguardando_escolha_horario com sugestões
        if ctx.get("modo_escolha_horario"):
            print(f"  ✅ PASS: Sistema reconheceu conflito e pediu escolher horário")
        else:
            print(f"  ❌ FAIL: Sistema não detectou conflito")
            assert False, "Conflito não detectado"

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        print(f"\n  RESULT: Teste Conflito PASSED")
        return True


if __name__ == "__main__":
    import asyncio

    async def main():
        teste = TestConflitoDraftPersistencia()
        try:
            await teste.test_conflito_bruna_27_outubro_10h()
            print("\n[FINAL] Teste PASSOU ✅")
        except Exception as e:
            print(f"\n[FINAL] Teste FALHOU ❌: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(main())
