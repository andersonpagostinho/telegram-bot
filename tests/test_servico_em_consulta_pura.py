#!/usr/bin/env python3
"""
Teste: Serviço deve ser capturado quando mencionado em pergunta informativa,
mesmo durante uma "consulta pura" (descobrir_servico_para_consulta).

Replicar fluxo do log real:
1. Cliente: "a bruna esta disponivel amanha as 10?" (sem serviço)
2. Sistema: "Qual serviço você quer fazer?"
3. Cliente: "fora ela, tem alguma outra que faz manicure?" (mencionando serviço)
4. ESPERADO: draft["servico"] deve ser atualizado com "manicure"
5. Sistema: Oferece profissionais que fazem manicure
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


async def main():
    tenant_id = "7394370553"
    wa_id = "5511991382080"

    print("\n" + "="*70)
    print("TESTE: Capturar serviço em consulta pura")
    print("="*70)

    # ═══════════════════════════════════════════════════════════
    # M1: Cliente: "a bruna esta disponivel amanha as 10?"
    # ═══════════════════════════════════════════════════════════
    print("\n[M1] Cliente: 'a bruna esta disponivel amanha as 10?'")

    ctx_m1 = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "objetivo_conversacional": None,
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{wa_id}",
        dados=ctx_m1
    )

    resultado_m1 = await roteador_principal(
        user_id=wa_id,
        mensagem="a bruna esta disponivel amanha as 10?",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_m1 = resultado_m1.get("resposta", "")
    print(f"[S1] Sistema: {resposta_m1[:100]}")

    # Verificar contexto após M1
    ctx_pos_m1 = await buscar_dado_em_path(path=f"Clientes/{tenant_id}/Sessoes/{wa_id}")
    draft_m1 = ctx_pos_m1.get("draft_agendamento") or {}
    print(f"[DEBUG-M1] draft após resposta: {draft_m1}")
    print(f"[DEBUG-M1] estado_fluxo: {ctx_pos_m1.get('estado_fluxo')}")
    print(f"[DEBUG-M1] objetivo_conversacional: {ctx_pos_m1.get('objetivo_conversacional')}")

    # ═══════════════════════════════════════════════════════════
    # M2: Cliente: "fora ela, tem alguma outra que faz manicure?"
    # ═══════════════════════════════════════════════════════════
    print("\n[M2] Cliente: 'fora ela, tem alguma outra que faz manicure?'")

    resultado_m2 = await roteador_principal(
        user_id=wa_id,
        mensagem="fora ela, tem alguma outra que faz manicure?",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_m2 = resultado_m2.get("resposta", "")
    print(f"[S2] Sistema: {resposta_m2[:150]}")

    # Verificar contexto após M2 — ESTE É O PONTO CRÍTICO
    ctx_pos_m2 = await buscar_dado_em_path(path=f"Clientes/{tenant_id}/Sessoes/{wa_id}")
    draft_m2 = ctx_pos_m2.get("draft_agendamento") or {}

    print(f"\n[DEBUG-M2-DRAFT] {draft_m2}")
    print(f"[DEBUG-M2] estado_fluxo: {ctx_pos_m2.get('estado_fluxo')}")
    print(f"[DEBUG-M2] objetivo_conversacional: {ctx_pos_m2.get('objetivo_conversacional')}")
    print(f"[DEBUG-M2] intencao_conversacional: {ctx_pos_m2.get('intencao_conversacional')}")

    # ═══════════════════════════════════════════════════════════
    # VALIDAÇÕES
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("VALIDAÇÕES")
    print("="*70)

    # V1: draft deve ter data_hora após M1
    assert draft_m1.get("data_hora"), "❌ M1: draft deveria ter data_hora"
    print("✅ V1: draft tem data_hora após M1")

    # V2: draft deve ter servico após M2 (CRÍTICO)
    if draft_m2.get("servico"):
        print(f"✅ V2 CRÍTICO: draft tem servico após M2: {draft_m2.get('servico')}")
    else:
        print(f"❌ V2 CRÍTICO FALHOU: draft.servico = {draft_m2.get('servico')} (esperado: manicure ou similar)")

    # V3: estado_fluxo deve mudar para aguardando_profissional ou manter aguardando_servico
    print(f"ℹ️  V3: estado_fluxo = {ctx_pos_m2.get('estado_fluxo')}")

    # V4: resposta deve listar profissionais que fazem manicure
    resposta_normalizada = resposta_m2.lower()
    if "gloria" in resposta_normalizada or "joana" in resposta_normalizada or "bruna" in resposta_normalizada:
        print("✅ V4: resposta lista profissionais para manicure")
    else:
        print("❌ V4 FALHOU: resposta não lista profissionais")
        print(f"   Resposta: {resposta_m2}")

    # ═══════════════════════════════════════════════════════════
    # M3: Cliente: "ok pode ser com a bruna"
    # ═══════════════════════════════════════════════════════════
    print("\n[M3] Cliente: 'ok pode ser com a bruna'")

    resultado_m3 = await roteador_principal(
        user_id=wa_id,
        mensagem="ok pode ser com a bruna",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta_m3 = resultado_m3.get("resposta", "")
    print(f"[S3] Sistema: {resposta_m3[:150]}")

    ctx_pos_m3 = await buscar_dado_em_path(path=f"Clientes/{tenant_id}/Sessoes/{wa_id}")
    draft_m3 = ctx_pos_m3.get("draft_agendamento") or {}

    print(f"\n[DEBUG-M3-DRAFT] {draft_m3}")

    # V5: M3 resposta deve ter confirmado o agendamento ou estar pronto para confirmar
    if "manicure" in resposta_m3.lower() and ("bruna" in resposta_m3.lower() or "amanhã" in resposta_m3.lower()):
        print("✅ V5: resposta confirma os dados corretos (manicure + bruna + data)")
    else:
        print(f"⚠️  V5: resposta pode estar incompleta. Resposta: {resposta_m3[:100]}")

    print("\n" + "="*70)
    print("TESTE CONCLUÍDO")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
