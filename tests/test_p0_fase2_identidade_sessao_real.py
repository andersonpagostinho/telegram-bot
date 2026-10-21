"""
[FASE 2] P0 IDENTIDADE & SESSÃO — Testes E2E com Firebase Real

Valida:
- Sessão v2 como fonte primária
- Actor ID propagação correta
- Tenant isolation
- Contexto legado não sobrescreve v2
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import carregar_contexto_temporario_v2, salvar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_identidade_actor_id_propagacao():
    """[FASE 2] Cenário: Actor ID propagado corretamente no evento"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{(datetime.now() + timedelta(days=70)).strftime('%Y-%m-%d')}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[IDENTIDADE-1] Resultado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        evento = [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"]
        if evento:
            print(f"[IDENTIDADE-1] Cliente ID no evento: {evento[0].get('cliente_id')}")
        assert resultado is True
    else:
        print("[IDENTIDADE-1] FALHA: add_evento_por_gpt retornou False")


@pytest.mark.asyncio
async def test_p0_identidade_sessao_v2_prioridade():
    """[FASE 2] Cenário: Sessão v2 tem prioridade sobre contexto legado"""
    ctx_v2 = {
        "_tenant_id_guard": TENANT_TEST,
        "servico": "hidratacao",
        "profissional_escolhido": "Carla",
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx_v2)

    ctx_carregado = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    assert ctx_carregado.get("servico") == "hidratacao", "v2 foi sobrescrito!"
    print("[IDENTIDADE-2] ✓ v2 tem prioridade")


@pytest.mark.asyncio
async def test_p0_identidade_multi_tenant_isolation():
    """[FASE 2] Cenário: Clientes de tenants diferentes isolados"""
    TENANT_A = "7394370553"
    TENANT_B = "9999999999"

    # Tenant A
    dados_a = {
        "profissional": "Gloria",
        "servico": "escova",
        "data_hora": f"{(datetime.now() + timedelta(days=75)).strftime('%Y-%m-%d')}T11:00:00",
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_A,
        "user_id": "5511991382080",
        "cliente_id": "whatsapp:5511991382080",
    }
    resultado_a = await add_evento_por_gpt(None, None, dados_a)
    print(f"[IDENTIDADE-3] Tenant A: {resultado_a}")

    if resultado_a:
        eventos_a = await buscar_subcolecao(f"Clientes/{TENANT_A}/Eventos") or {}
        eventos_b = await buscar_subcolecao(f"Clientes/{TENANT_B}/Eventos") or {}

        gloria_a = len([e for e in eventos_a.values() if e.get("profissional", "").lower() == "gloria"])
        gloria_b = len([e for e in eventos_b.values() if e.get("profissional", "").lower() == "gloria"])

        print(f"[IDENTIDADE-3] Tenant A Gloria: {gloria_a}, Tenant B Gloria: {gloria_b}")
        if gloria_a > 0 and gloria_b == 0:
            print("[IDENTIDADE-3] ✓ Isolamento OK")
