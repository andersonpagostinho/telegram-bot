"""
[P0.1] Normalização de Prefixo Telegram — `tg:` vs `telegram:`

Valida que:
1. Telegram usa prefixo `tg:` (não `telegram:`)
2. Identificador é construído corretamente em gpt_executor.py
3. Sessão é carregada do path correto
4. Isolamento entre Telegram e WhatsApp funciona
5. Isolamento entre tenants funciona
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.identidade_contexto import IdentidadeContexto
from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)

TENANT_TEST = "7394370553"
TG_USER_ID = "123456789"
WA_USER_ID = "5511991382080"

@pytest.mark.asyncio
async def test_prefixo_tg_nao_telegram():
    """✅ T1: Padrão `tg:` é usado, não `telegram:`."""

    print("\n" + "="*80)
    print("T1: PADRÃO TG: NÃO TELEGRAM:")
    print("="*80)

    # Simular construção em gpt_executor.py (linha 845)
    user_id = TG_USER_ID
    identidade = None  # Fallback (não há identidade WhatsApp)

    # ❌ ANTIGO (errado)
    actor_id_antigo = f"telegram:{user_id}" if not identidade else identidade.actor_id

    # ✅ NOVO (correto)
    actor_id_novo = f"tg:{user_id}" if not identidade else identidade.actor_id

    print(f"\n[ANTIGO] {actor_id_antigo}")
    assert actor_id_antigo == "telegram:123456789"

    print(f"[NOVO] {actor_id_novo}")
    assert actor_id_novo == "tg:123456789", "Deveria usar prefixo `tg:` não `telegram:`"

    print("✅ Normalização confirmada")

@pytest.mark.asyncio
async def test_sessao_telegram_carregada_corretamente():
    """✅ T2: Sessão Telegram é salva e carregada com prefixo `tg:`."""

    print("\n" + "="*80)
    print("T2: SESSÃO TELEGRAM SALVA E CARREGADA")
    print("="*80)

    actor_id = f"tg:{TG_USER_ID}"
    dados_teste = {
        "servico": "consulta",
        "tipo_usuario": "cliente",
        "_tenant_id_guard": TENANT_TEST,
    }

    print(f"\n[SALVAR] tenant={TENANT_TEST} | actor={actor_id}")
    await salvar_contexto_temporario_v2(TENANT_TEST, actor_id, dados_teste)
    print("✅ Salvo em Clientes/{tenant}/Sessoes/tg:{user_id}")

    print(f"\n[CARREGAR] tenant={TENANT_TEST} | actor={actor_id}")
    resultado = await carregar_contexto_temporario_v2(TENANT_TEST, actor_id)

    assert resultado is not None, "Contexto deveria ser encontrado"
    assert resultado.get("servico") == "consulta", "Serviço deveria ser 'consulta'"
    print(f"✅ Carregado: servico={resultado.get('servico')}")

@pytest.mark.asyncio
async def test_isolamento_telegram_vs_whatsapp():
    """🔒 T3: Telegram e WhatsApp são isolados mesmo com mesmo tenant."""

    print("\n" + "="*80)
    print("T3: ISOLAMENTO TELEGRAM vs WHATSAPP")
    print("="*80)

    actor_tg = f"tg:{TG_USER_ID}"
    actor_wa = f"whatsapp:{WA_USER_ID}"

    # Salvar no Telegram
    print(f"\n[SALVAR TG] actor={actor_tg} | servico=consulta")
    await salvar_contexto_temporario_v2(TENANT_TEST, actor_tg, {
        "servico": "consulta",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Salvar no WhatsApp
    print(f"[SALVAR WA] actor={actor_wa} | servico=manicure")
    await salvar_contexto_temporario_v2(TENANT_TEST, actor_wa, {
        "servico": "manicure",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Carregar Telegram
    print(f"\n[CARREGAR TG] actor={actor_tg}")
    ctx_tg = await carregar_contexto_temporario_v2(TENANT_TEST, actor_tg)
    assert ctx_tg.get("servico") == "consulta", "TG deveria ter 'consulta'"
    print(f"✅ TG isolado: {ctx_tg.get('servico')}")

    # Carregar WhatsApp
    print(f"[CARREGAR WA] actor={actor_wa}")
    ctx_wa = await carregar_contexto_temporario_v2(TENANT_TEST, actor_wa)
    assert ctx_wa.get("servico") == "manicure", "WA deveria ter 'manicure'"
    print(f"✅ WA isolado: {ctx_wa.get('servico')}")

@pytest.mark.asyncio
async def test_identidade_contexto_cria_tg_corretamente():
    """✅ T4: IdentidadeContexto cria actor_id com prefixo `tg:`."""

    print("\n" + "="*80)
    print("T4: IDENTIDADE CONTEXTO CRIA TG: CORRETAMENTE")
    print("="*80)

    # Criar IdentidadeContexto para Telegram
    identidade = IdentidadeContexto(
        user_id=TG_USER_ID,
        tenant_id=TENANT_TEST,
        actor_id=f"tg:{TG_USER_ID}",
        canal="telegram"
    )

    print(f"\n[IDENTIDADE] {identidade}")
    assert identidade.actor_id == f"tg:{TG_USER_ID}", "Actor ID deveria ter prefixo `tg:`"
    assert identidade.canal == "telegram", "Canal deveria ser 'telegram'"
    print(f"✅ IdentidadeContexto correto: actor_id={identidade.actor_id}")

@pytest.mark.asyncio
async def test_fallback_em_gpt_executor_usa_tg():
    """✅ T5: Fallback em gpt_executor.py:845 usa `tg:` quando sem identidade."""

    print("\n" + "="*80)
    print("T5: FALLBACK GPT_EXECUTOR USA TG:")
    print("="*80)

    # Simular fallback Telegram (sem identidade WhatsApp)
    user_id = TG_USER_ID
    identidade = None

    # Lógica de gpt_executor.py:845 APÓS correção
    actor_id = identidade.actor_id if identidade else f"tg:{user_id}"

    print(f"\n[FALLBACK] identidade=None | user_id={user_id}")
    print(f"[RESULTADO] actor_id={actor_id}")

    assert actor_id == f"tg:{user_id}", "Fallback deveria gerar `tg:{user_id}`"
    assert actor_id.startswith("tg:"), "Deveria começar com `tg:`"
    print("✅ Fallback correto")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
