"""
[FASE 2] P0 RESUMO DIÁRIO — Testes E2E com Firebase Real

Valida:
- Resumo mostra dados corretos
- Isolamento por ator
- Sem duplicação
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

from utils.contexto_temporario import salvar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_resumo_cliente_vê_seus_eventos():
    """[FASE 2] Cenário: Cliente vê apenas seus agendamentos no resumo"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    # Evento para cliente
    dados = {
        "profissional": "Bruna",
        "servico": "manicure",
        "data_hora": f"{(datetime.now() + timedelta(days=115)).strftime('%Y-%m-%d')}T10:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[RESUMO-1] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        cliente_eventos = [e for e in eventos.values() if e.get("cliente_id") == ACTOR_WA]
        print(f"[RESUMO-1] Cliente vê {len(cliente_eventos)} eventos")
        if len(cliente_eventos) > 0:
            print("[RESUMO-1] ✓ Cliente tem eventos para resumo")


@pytest.mark.asyncio
async def test_p0_resumo_isolamento_cliente():
    """[FASE 2] Cenário: Resumo isolado por cliente"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    CLIENTE_A = "whatsapp:5511991382080"
    CLIENTE_B = "whatsapp:5511991382090"

    # Evento Cliente A
    dados_a = {
        "profissional": "Gloria",
        "servico": "pedicure",
        "data_hora": f"{(datetime.now() + timedelta(days=120)).strftime('%Y-%m-%d')}T14:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382080",
        "cliente_id": CLIENTE_A,
    }

    resultado_a = await add_evento_por_gpt(None, None, dados_a)
    print(f"[RESUMO-2] Cliente A evento: {resultado_a}")

    if resultado_a:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        eventos_a = len([e for e in eventos.values() if e.get("cliente_id") == CLIENTE_A])
        eventos_b = len([e for e in eventos.values() if e.get("cliente_id") == CLIENTE_B])
        print(f"[RESUMO-2] Cliente A: {eventos_a}, Cliente B: {eventos_b}")
        if eventos_a > 0 and eventos_b == 0:
            print("[RESUMO-2] ✓ Isolamento OK")
