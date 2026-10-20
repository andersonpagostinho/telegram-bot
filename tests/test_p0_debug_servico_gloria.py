"""
[P0 DEBUG] Teste para Debugar por que "gloria" muda serviço de "corte feminino" para "coloracao"

Fluxo:
1. MSG1: "voce tem agenda para corte feminino amanha as 10?"
   → Esperado: servico='corte feminino'

2. MSG2: "gloria"
   → Esperado: servico='corte feminino' (PRESERVADO)
   → PROBLEMA REAL: servico='coloracao' (TROCADO!)

3. Debugar exatamente onde a troca acontece
"""

import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)
from router.principal_router import extrair_slots_e_mesclar
from services.firebase_service_async import buscar_subcolecao

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_debug_gloria_servico():
    """
    Teste DEBUG: MSG1 → MSG2 com prints detalhados
    """
    print("\n" + "="*100)
    print("[P0 DEBUG] TESTE PARA DEBUGAR TROCA DE SERVIÇO")
    print("="*100)

    # Setup: carregar profissionais
    profs_dict = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Profissionais") or {}
    if not profs_dict:
        pytest.skip("Tenant sem profissionais")

    prof_nomes = [p.get("nome") for p in profs_dict.values() if p.get("nome")]
    print(f"\n✓ Profissionais disponíveis: {prof_nomes}")

    # ============================================================================
    # PASSO 1: Limpar sessão
    # ============================================================================
    print("\n[PASSO 1] Limpar contexto inicial")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {
        "_tenant_id_guard": TENANT_TEST,
    })
    print("✓ Contexto limpo")

    # ============================================================================
    # PASSO 2: MSG1 — "voce tem agenda para corte feminino amanha as 10?"
    # ============================================================================
    print("\n[PASSO 2] Processar MSG1: 'voce tem agenda para corte feminino amanha as 10?'")
    print("-" * 100)

    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}

    # Chamar extrair_slots_e_mesclar
    ctx = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="voce tem agenda para corte feminino amanha as 10?",
        dono_id=TENANT_TEST,
        cliente_id=ACTOR_WA
    )

    servico_msg1 = ctx.get("servico")
    data_hora_msg1 = ctx.get("data_hora")

    print(f"\n✓ MSG1 resultado:")
    print(f"  servico={servico_msg1}")
    print(f"  data_hora={data_hora_msg1}")

    assert servico_msg1 == "corte feminino", f"MSG1: Esperado 'corte feminino', recebido '{servico_msg1}'"

    # Salvar contexto
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)
    print("✓ Contexto salvo")

    # ============================================================================
    # PASSO 3: MSG2 — "gloria"
    # ============================================================================
    print("\n[PASSO 3] Processar MSG2: 'gloria'")
    print("-" * 100)

    # Carregar contexto (que tem servico='corte feminino')
    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}
    print(f"\n[ANTES MSG2] ctx['servico']={ctx.get('servico')}")

    # Chamar extrair_slots_e_mesclar NOVAMENTE
    ctx = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="gloria",
        dono_id=TENANT_TEST,
        cliente_id=ACTOR_WA
    )

    servico_msg2 = ctx.get("servico")
    prof_msg2 = ctx.get("profissional_escolhido")

    print(f"\n✓ MSG2 resultado:")
    print(f"  servico={servico_msg2}")
    print(f"  profissional_escolhido={prof_msg2}")

    # VALIDAÇÃO CRÍTICA
    if servico_msg2 == "corte feminino":
        print("\n✅ [SUCESSO] Serviço preservado corretamente!")
    else:
        print(f"\n❌ [FALHA] Serviço foi trocado: 'corte feminino' → '{servico_msg2}'")

    # Salvar para análise
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    assert servico_msg2 == "corte feminino", \
        f"MSG2: Esperado serviço 'corte feminino' PRESERVADO, mas recebido '{servico_msg2}'"

    print("\n" + "="*100)
    print("✅ TESTE PASSOU: Serviço preservado corretamente entre MSG1 e MSG2")
    print("="*100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
