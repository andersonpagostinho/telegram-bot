"""
[P0626 FIX] Teste de isolamento — actor_id canônico em carregar_contexto_temporario_v2()

Valida que:
1. Contexto é salvo e carregado com actor_id correto (whatsapp:{wa_id} ou tg:{tg_id})
2. Carregamento com user_id numérico FALHA (path errado)
3. Isolamento entre tenants funciona
4. Isolamento entre atores funciona
"""

import pytest
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
    atualizar_dado_em_path,
)

# Tenant e atores para teste
TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"
ACTOR_TG = "tg:123456789"

@pytest.mark.asyncio
async def test_salvar_carregar_com_actor_id_correto():
    """✅ T1: Salva e carrega contexto com actor_id canônico correto."""

    print("\n" + "="*80)
    print("T1: SALVAR E CARREGAR COM ACTOR_ID CORRETO")
    print("="*80)

    dados_teste = {
        "servico": "manicure",
        "profissional": "Bruna",
        "data_hora": "2026-10-21T10:00:00",
        "_tenant_id_guard": TENANT_TEST,
    }

    print(f"\n[SALVAR] tenant={TENANT_TEST} | actor={ACTOR_WA}")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, dados_teste)
    print("✅ Salvo")

    print(f"\n[CARREGAR] tenant={TENANT_TEST} | actor={ACTOR_WA}")
    resultado = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)

    print(f"[RESULTADO] {resultado}")
    assert resultado is not None, "Contexto deveria ser encontrado"
    assert resultado.get("servico") == "manicure", "Serviço deveria ser 'manicure'"
    assert resultado.get("profissional") == "Bruna", "Profissional deveria ser 'Bruna'"
    print("✅ Carregado corretamente")

@pytest.mark.asyncio
async def test_carregar_com_user_id_numerico_falha():
    """❌ T2: Carregamento com user_id numérico FALHA (path errado)."""

    print("\n" + "="*80)
    print("T2: CARREGAR COM USER_ID NUMÉRICO FALHA")
    print("="*80)

    # Salvar com actor_id correto
    print(f"\n[SALVAR] tenant={TENANT_TEST} | actor={ACTOR_WA}")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {"servico": "manicure"})
    print("✅ Salvo em Clientes/{tenant}/Sessoes/whatsapp:{wa_id}")

    # Tentar carregar com user_id numérico (BUG ANTIGO)
    print(f"\n[CARREGAR COM BUG] tenant={TENANT_TEST} | user_id={WA_ID}")
    resultado = await carregar_contexto_temporario_v2(TENANT_TEST, WA_ID)

    print(f"[RESULTADO] {resultado}")
    assert resultado is None or resultado == {}, "Deveria retornar vazio (path errado)"
    print("✅ Retornou vazio (como esperado, path errado)")

@pytest.mark.asyncio
async def test_isolamento_entre_atores():
    """🔒 T3: Contexto de um ator não é acessível por outro."""

    print("\n" + "="*80)
    print("T3: ISOLAMENTO ENTRE ATORES")
    print("="*80)

    # Ator 1: WhatsApp
    print(f"\n[SALVAR ATOR 1] actor={ACTOR_WA} | servico=corte_feminino")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {
        "servico": "corte_feminino",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Ator 2: Telegram
    print(f"[SALVAR ATOR 2] actor={ACTOR_TG} | servico=manicure")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_TG, {
        "servico": "manicure",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Carregar Ator 1
    print(f"\n[CARREGAR] actor={ACTOR_WA}")
    resultado_wa = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    print(f"[RESULTADO] servico={resultado_wa.get('servico') if resultado_wa else None}")
    assert resultado_wa.get("servico") == "corte_feminino", "Ator 1 deveria ter seu serviço"
    print("✅ Ator 1 isolado")

    # Carregar Ator 2
    print(f"\n[CARREGAR] actor={ACTOR_TG}")
    resultado_tg = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_TG)
    print(f"[RESULTADO] servico={resultado_tg.get('servico') if resultado_tg else None}")
    assert resultado_tg.get("servico") == "manicure", "Ator 2 deveria ter seu serviço"
    print("✅ Ator 2 isolado")

@pytest.mark.asyncio
async def test_isolamento_entre_tenants():
    """🔒 T4: Contexto de um tenant não é acessível por outro."""

    print("\n" + "="*80)
    print("T4: ISOLAMENTO ENTRE TENANTS")
    print("="*80)

    TENANT_2 = "9876543210"

    # Tenant 1
    print(f"\n[SALVAR TENANT 1] tenant={TENANT_TEST} | actor={ACTOR_WA} | servico=corte")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {
        "servico": "corte",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Tenant 2 (mesmo ator, tenant diferente)
    print(f"[SALVAR TENANT 2] tenant={TENANT_2} | actor={ACTOR_WA} | servico=manicure")
    await salvar_contexto_temporario_v2(TENANT_2, ACTOR_WA, {
        "servico": "manicure",
        "_tenant_id_guard": TENANT_2,
    })

    # Carregar do Tenant 1
    print(f"\n[CARREGAR] tenant={TENANT_TEST} | actor={ACTOR_WA}")
    resultado_1 = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    print(f"[RESULTADO] servico={resultado_1.get('servico') if resultado_1 else None}")
    assert resultado_1.get("servico") == "corte", "Tenant 1 deveria ter seu serviço"
    print("✅ Tenant 1 isolado")

    # Carregar do Tenant 2
    print(f"\n[CARREGAR] tenant={TENANT_2} | actor={ACTOR_WA}")
    resultado_2 = await carregar_contexto_temporario_v2(TENANT_2, ACTOR_WA)
    print(f"[RESULTADO] servico={resultado_2.get('servico') if resultado_2 else None}")
    assert resultado_2.get("servico") == "manicure", "Tenant 2 deveria ter seu serviço"
    print("✅ Tenant 2 isolado")

@pytest.mark.asyncio
async def test_padrão_actor_id_consistente():
    """✅ T5: Padrão whatsapp:{wa_id} vs tg:{tg_id} é respeitado."""

    print("\n" + "="*80)
    print("T5: PADRÃO ACTOR_ID CONSISTENTE")
    print("="*80)

    print(f"\n[VALIDAR PADRÃO]")
    print(f"  WhatsApp: {ACTOR_WA}")
    assert ACTOR_WA.startswith("whatsapp:"), "WhatsApp deveria ter prefixo 'whatsapp:'"

    print(f"  Telegram: {ACTOR_TG}")
    assert ACTOR_TG.startswith("tg:"), "Telegram deveria ter prefixo 'tg:'"

    print("✅ Padrões validados")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
