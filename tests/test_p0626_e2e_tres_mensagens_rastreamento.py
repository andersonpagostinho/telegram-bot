"""
[P0626] Teste E2E Três Mensagens — Rastreamento Granular de Contexto

Fluxo real:
1. MSG 1: User envia frase com serviço ("voce tem agenda para corte feminino amanha as 10?")
2. MSG 2: Sistema responde, User confirma/responde
3. MSG 3: Continuação, Sistema cria evento

Objetivo: Identificar EXATAMENTE onde o serviço desaparece entre MSG 1-3
"""

import pytest
import sys
import time
import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

with patch("scheduler.notificacoes_scheduler.start_notificacao_scheduler"):
    import main
    app = main.app

from utils.contexto_temporario import carregar_contexto_temporario_v2, atualizar_dado_em_path

# Teste com cliente real
TENANT = "7394370553"
USER_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{USER_ID}"
PHONE_ID = "1350170954840548"

# Para capturar respostas
respostas_capturadas = []

def criar_payload_whatsapp(texto: str, msg_id: str) -> dict:
    """Cria payload sintético WhatsApp para teste"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1630189518519404",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "5519994443694", "phone_number_id": PHONE_ID},
                    "contacts": [{"profile": {"name": "Teste"}, "wa_id": USER_ID}],
                    "messages": [{
                        "from": USER_ID,
                        "id": msg_id,
                        "timestamp": str(int(time.time())),
                        "text": {"body": texto},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

@pytest.mark.asyncio
async def test_p0626_tres_mensagens_rastreamento():
    """
    🧪 TESTE E2E TRÊS MENSAGENS COM RASTREAMENTO GRANULAR

    Valida: serviço persiste de MSG 1 → MSG 2 → MSG 3
    """

    print("\n" + "="*80)
    print("🧪 TESTE E2E TRÊS MENSAGENS — RASTREAMENTO P0626")
    print("="*80)

    client = app.test_client()

    # ✅ LIMPEZA INICIAL
    print("\n[PREP] Limpando estado anterior...")
    await atualizar_dado_em_path(
        path=f"Clientes/{TENANT}/Sessoes/{ACTOR_ID}",
        dados={
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "servico": None,
            "servico_sugerido_consulta": None,
            "draft_agendamento": None,
            "multiplos_servicos_candidatos": None,
        }
    )
    print("✅ Estado limpo")

    # ═════════════════════════════════════════════════════════════════════════
    # MSG 1: Consulta com serviço
    # ═════════════════════════════════════════════════════════════════════════

    print("\n" + "-"*80)
    print("[MSG 1] Consulta: 'voce tem agenda para corte feminino amanha as 10?'")
    print("-"*80)

    payload_msg1 = criar_payload_whatsapp(
        "voce tem agenda para corte feminino amanha as 10?",
        f"msg1_{int(time.time() * 1000)}"
    )

    with patch("main.validate_whatsapp_signature", return_value=True):
        response1 = client.post("/webhook/whatsapp", json=payload_msg1)

    print(f"[HTTP] Status: {response1.status_code}")
    assert response1.status_code == 200

    await asyncio.sleep(1.0)  # Aguardar processamento assíncrono

    ctx1 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    print(f"\n[CTX 1 CARREGADO]")
    print(f"  estado_fluxo: {ctx1.get('estado_fluxo')}")
    print(f"  intencao_conversacional: {ctx1.get('intencao_conversacional')}")
    print(f"  servico: {ctx1.get('servico')}")
    print(f"  servico_sugerido_consulta: {ctx1.get('servico_sugerido_consulta')}")
    print(f"  draft_agendamento: {ctx1.get('draft_agendamento')}")
    print(f"  multiplos_servicos_candidatos: {ctx1.get('multiplos_servicos_candidatos')}")

    # Validação MSG 1
    servico_msg1 = ctx1.get('servico') or ctx1.get('servico_sugerido_consulta')
    print(f"\n[VALIDACAO MSG 1]")
    if servico_msg1:
        print(f"✅ Serviço extraído: '{servico_msg1}'")
    else:
        print(f"❌ Serviço NÃO extraído!")
        print(f"\nContexto completo: {json.dumps(ctx1, indent=2, default=str)}")

    # ═════════════════════════════════════════════════════════════════════════
    # MSG 2: Resposta do usuário
    # ═════════════════════════════════════════════════════════════════════════

    print("\n" + "-"*80)
    print("[MSG 2] Resposta/Continuação do fluxo")
    print("-"*80)

    # Determinar qual deve ser MSG 2 baseado no estado de MSG 1
    estado_msg1 = ctx1.get('estado_fluxo', 'idle')

    if estado_msg1 == 'aguardando_servico':
        msg2_texto = "manicure"  # Responder qual serviço
        print(f"Estado: aguardando_servico → Enviando: '{msg2_texto}'")
    elif estado_msg1 == 'idle':
        msg2_texto = "sim"  # Assumir que sistema perguntou "quer agendar?"
        print(f"Estado: idle → Enviando: '{msg2_texto}'")
    else:
        msg2_texto = "sim"  # Default
        print(f"Estado: {estado_msg1} → Enviando: '{msg2_texto}' (default)")

    payload_msg2 = criar_payload_whatsapp(
        msg2_texto,
        f"msg2_{int(time.time() * 1000)}"
    )

    with patch("main.validate_whatsapp_signature", return_value=True):
        response2 = client.post("/webhook/whatsapp", json=payload_msg2)

    print(f"[HTTP] Status: {response2.status_code}")
    assert response2.status_code == 200

    await asyncio.sleep(1.0)

    ctx2 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    print(f"\n[CTX 2 CARREGADO]")
    print(f"  estado_fluxo: {ctx2.get('estado_fluxo')}")
    print(f"  servico: {ctx2.get('servico')}")
    print(f"  servico_sugerido_consulta: {ctx2.get('servico_sugerido_consulta')}")
    print(f"  draft_agendamento: {bool(ctx2.get('draft_agendamento'))}")
    print(f"  data_hora: {ctx2.get('data_hora')}")

    # Validação MSG 2
    servico_msg2 = ctx2.get('servico') or ctx2.get('servico_sugerido_consulta')
    print(f"\n[VALIDACAO MSG 2]")
    if servico_msg2:
        print(f"✅ Serviço preservado: '{servico_msg2}'")
    else:
        print(f"❌ Serviço PERDIDO entre MSG 1 e MSG 2!")

    # ═════════════════════════════════════════════════════════════════════════
    # MSG 3: Continuação/Confirmação
    # ═════════════════════════════════════════════════════════════════════════

    print("\n" + "-"*80)
    print("[MSG 3] Confirmação/Continuação")
    print("-"*80)

    estado_msg2 = ctx2.get('estado_fluxo', 'idle')

    if estado_msg2 in ['aguardando_confirmacao_agendamento', 'aguardando_confirmacao']:
        msg3_texto = "sim"  # Confirmar
        print(f"Estado: {estado_msg2} → Enviando confirmação: '{msg3_texto}'")
    elif estado_msg2 == 'aguardando_profissional':
        msg3_texto = "Bruna"  # Escolher profissional
        print(f"Estado: aguardando_profissional → Enviando: '{msg3_texto}'")
    elif estado_msg2 == 'aguardando_horario':
        msg3_texto = "14h"  # Escolher horário
        print(f"Estado: aguardando_horario → Enviando: '{msg3_texto}'")
    else:
        msg3_texto = "sim"  # Default
        print(f"Estado: {estado_msg2} → Enviando: '{msg3_texto}' (default)")

    payload_msg3 = criar_payload_whatsapp(
        msg3_texto,
        f"msg3_{int(time.time() * 1000)}"
    )

    with patch("main.validate_whatsapp_signature", return_value=True):
        response3 = client.post("/webhook/whatsapp", json=payload_msg3)

    print(f"[HTTP] Status: {response3.status_code}")
    assert response3.status_code == 200

    await asyncio.sleep(1.0)

    ctx3 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    print(f"\n[CTX 3 CARREGADO]")
    print(f"  estado_fluxo: {ctx3.get('estado_fluxo')}")
    print(f"  servico: {ctx3.get('servico')}")
    print(f"  servico_sugerido_consulta: {ctx3.get('servico_sugerido_consulta')}")
    print(f"  draft_agendamento: {bool(ctx3.get('draft_agendamento'))}")
    print(f"  evento_criado: {ctx3.get('evento_criado')}")

    # Validação MSG 3
    servico_msg3 = ctx3.get('servico') or ctx3.get('servico_sugerido_consulta')
    print(f"\n[VALIDACAO MSG 3]")
    if servico_msg3:
        print(f"✅ Serviço mantido: '{servico_msg3}'")
    else:
        print(f"❌ Serviço PERDIDO em MSG 3!")
        print(f"   Isso é onde o evento validation falha com [P0626_VALIDACAO]")

    # ═════════════════════════════════════════════════════════════════════════
    # RELATÓRIO FINAL
    # ═════════════════════════════════════════════════════════════════════════

    print("\n" + "="*80)
    print("📊 RELATÓRIO FINAL")
    print("="*80)

    print(f"\n[CADEIA DE ESTADOS]")
    print(f"MSG 1 → estado: {ctx1.get('estado_fluxo')}, servico: {servico_msg1}")
    print(f"MSG 2 → estado: {ctx2.get('estado_fluxo')}, servico: {servico_msg2}")
    print(f"MSG 3 → estado: {ctx3.get('estado_fluxo')}, servico: {servico_msg3}")

    print(f"\n[PERSISTÊNCIA]")
    print(f"MSG 1 salvou em: Clientes/{TENANT}/Sessoes/{ACTOR_ID}")
    print(f"MSG 2 carregou de: Clientes/{TENANT}/Sessoes/{ACTOR_ID}")
    print(f"MSG 3 carregou de: ? (precisa rastrear qual função é chamada)")

    print(f"\n[CONCLUSÃO]")
    if servico_msg3:
        print(f"✅ SERVIÇO PERSISTIU ATÉ MSG 3")
        print(f"   Fluxo completo funcionando")
    else:
        print(f"❌ SERVIÇO PERDIDO ANTES DE MSG 3")
        if servico_msg1 and not servico_msg2:
            print(f"   Culpado: Perda entre MSG 1 e MSG 2")
        elif servico_msg2 and not servico_msg3:
            print(f"   Culpado: Perda entre MSG 2 e MSG 3")
            print(f"   Provável causa: carregar_contexto_temporario() legado em MSG 3")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
