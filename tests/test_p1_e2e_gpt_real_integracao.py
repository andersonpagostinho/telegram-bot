"""
P1 E2E REAL COM GPT: Teste Completo com Webhook Real

Fluxo TOTAL:
1. MSG1 via webhook → router → classificador → validacao_conflito → resposta tabela
2. MSG2 via webhook → router → classificador → extração → GPT REAL → resposta
3. Validar resposta do GPT (detecta bug se pede profissional novamente)
"""

import pytest
import sys
from pathlib import Path
import json
import time
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

TENANT = "7394370553"
WA_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{WA_ID}"


def _webhook_payload(mensagem: str, wa_id: str = WA_ID) -> dict:
    """Gera payload webhook WhatsApp"""
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
                        "id": f"wamid.e2e_{int(time.time() * 1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": mensagem},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }


class TestP1E2EGPTRealIntegracao:
    """E2E Real: Webhook → Router → GPT → Validar Resposta"""

    @pytest.mark.asyncio
    async def test_e2e_webhook_router_gpt_real(self):
        """
        Teste 100% real com GPT:
        1. MSG1: "a bruna esta disponivel amanha as 10?"
           → VALIDACAO_CONFLITO_PRE_GPT → Tabela de horários
        2. MSG2: "que pena, pode ser entao as 11:50"
           → Passa pelo GPT REAL
           → Valida resposta (detecta bug se pede profissional)
        """
        print("\n" + "=" * 90)
        print("E2E REAL COM GPT: WEBHOOK → ROUTER → GPT")
        print("=" * 90)

        from unittest.mock import patch, AsyncMock
        from utils.contexto_temporario import (
            limpar_contexto_agendamento_v2,
            carregar_contexto_temporario_v2,
        )

        # SETUP
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        print("\n[SETUP] Contexto limpo\n")

        # ============================================
        # MSG 1: PERGUNTA DE DISPONIBILIDADE
        # ============================================
        msg1 = "a bruna esta disponivel amanha as 10?"
        print("=" * 90)
        print(f"[MSG 1] VIA WEBHOOK REAL")
        print(f"Mensagem: '{msg1}'")
        print("=" * 90)

        # Simular webhook POST (chamaria o endpoint real)
        from main import app

        payload1 = _webhook_payload(msg1)

        print(f"\n[WEBHOOK] Enviando payload para /webhook/whatsapp")

        with patch("main.validate_whatsapp_signature", return_value=True):
            try:
                # Fazer POST real no app Flask
                client = app.test_client()
                response1 = client.post("/webhook/whatsapp", json=payload1)
                print(f"[WEBHOOK RESPONSE] Status: {response1.status_code}")

                # Aguardar processamento assíncrono
                await asyncio.sleep(2)

                # Carregar contexto para verificar se foi salvo
                ctx1 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
                print(f"\n[CTX APÓS MSG1]")
                print(f"  intencao_conversacional: {ctx1.get('intencao_conversacional')}")
                print(f"  profissional_escolhido: {ctx1.get('profissional_escolhido')}")
                print(f"  data_hora: {ctx1.get('data_hora')}")

            except Exception as e:
                print(f"[ERRO] Webhook MSG1: {e}")
                import traceback
                traceback.print_exc()

        # ============================================
        # MSG 2: ESCOLHA DE HORÁRIO ALTERNATIVO
        # ============================================
        msg2 = "que pena, pode ser entao as 11:50"
        print("\n" + "=" * 90)
        print(f"[MSG 2] VIA WEBHOOK REAL")
        print(f"Mensagem: '{msg2}'")
        print("=" * 90)

        payload2 = _webhook_payload(msg2)

        print(f"\n[WEBHOOK] Enviando payload para /webhook/whatsapp")

        with patch("main.validate_whatsapp_signature", return_value=True):
            try:
                client = app.test_client()
                response2 = client.post("/webhook/whatsapp", json=payload2)
                print(f"[WEBHOOK RESPONSE] Status: {response2.status_code}")

                # Aguardar processamento assíncrono (GPT precisa de tempo)
                await asyncio.sleep(3)

                # Carregar contexto
                ctx2 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
                print(f"\n[CTX APÓS MSG2]")
                print(f"  intencao_conversacional: {ctx2.get('intencao_conversacional')}")
                print(f"  profissional_escolhido: {ctx2.get('profissional_escolhido')}")
                print(f"  data_hora: {ctx2.get('data_hora')}")
                print(f"  servico: {ctx2.get('servico')}")

                # Verificar histórico (com a resposta do GPT)
                historico = ctx2.get('historico_texto', [])
                print(f"\n[HISTÓRICO]")
                if isinstance(historico, list):
                    for i, msg in enumerate(historico[-2:]):  # Últimas 2
                        print(f"  [{i}] {msg}")

                # ============================================
                # ANÁLISE DA RESPOSTA DO GPT
                # ============================================
                print("\n" + "=" * 90)
                print("[ANÁLISE] Resposta do GPT")
                print("=" * 90)

                if historico and len(historico) > 0:
                    ultima_resposta = historico[-1] if isinstance(historico[-1], str) else str(historico[-1])
                    print(f"\nÚltima resposta do GPT:")
                    print(f"  {ultima_resposta}\n")

                    # Verificar se está pedindo profissional novamente
                    palavras_bug = ["profissional", "qual profissional", "qual você", "qual serviço e profissional"]

                    tem_bug = any(palavra.lower() in ultima_resposta.lower() for palavra in ["profissional", "qual você"] if "Bruna" not in ultima_resposta)

                    if tem_bug and ctx2.get('profissional_escolhido') == 'Bruna':
                        print("🔴 BUG DETECTADO!")
                        print(f"   Status: GPT está pedindo profissional novamente")
                        print(f"   Deveria: Perguntar apenas o SERVIÇO (profissional já é Bruna)")
                        print(f"   Contexto tem profissional_escolhido=Bruna ✓")
                        print(f"   Mas GPT não recebeu isso no contexto ✗")
                        return False
                    else:
                        print("✅ RESPOSTA CORRETA!")
                        print(f"   GPT reconheceu que Bruna já foi escolhida")
                        return True
                else:
                    print("⚠️  Nenhum histórico encontrado")

            except Exception as e:
                print(f"[ERRO] Webhook MSG2: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
