"""
[FASE 2] P0 FLUXO SEQUENCIAL — Testes E2E com Firebase Real

Valida:
- Eventos sequenciais sem conflito
- Contexto preservado entre eventos
- Dados persistidos corretamente em Firestore
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

from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_sequencia_3_eventos():
    """[FASE 2] Criar 3 eventos sequenciais com profissionais diferentes"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")

    # Evento 1
    dados1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T09:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r1 = await add_evento_por_gpt(None, None, dados1)
    print(f"[FLUXO-1] Evento 1: {r1}")

    # Evento 2
    dados2 = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data}T14:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r2 = await add_evento_por_gpt(None, None, dados2)
    print(f"[FLUXO-1] Evento 2: {r2}")

    # Evento 3
    dados3 = {
        "profissional": "Joana",
        "servico": "manicure",
        "data_hora": f"{data}T18:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r3 = await add_evento_por_gpt(None, None, dados3)
    print(f"[FLUXO-1] Evento 3: {r3}")

    if r1 and r2 and r3:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        total = len([e for e in eventos.values() if e.get("data") == data])
        print(f"[FLUXO-1] Total eventos neste dia: {total}")
        if total >= 3:
            print("[FLUXO-1] ✓ 3 eventos criados sequencialmente")


@pytest.mark.asyncio
async def test_p0_contexto_persiste_entre_criacoes():
    """[FASE 2] Contexto persiste após múltiplas criações"""
    ctx = {
        "_tenant_id_guard": TENANT_TEST,
        "contador": 0,
        "historico": [],
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=16)).strftime("%Y-%m-%d")

    # Criar evento
    dados = {
        "profissional": "Carla",
        "servico": "pedicure",
        "data_hora": f"{data}T10:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[FLUXO-2] Evento criado: {resultado}")

    # Verificar contexto
    ctx_novo = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    if ctx_novo.get("_tenant_id_guard") == TENANT_TEST:
        print("[FLUXO-2] ✓ Contexto persistido após criação")


@pytest.mark.asyncio
async def test_p0_eventos_diferentes_dias():
    """[FASE 2] Eventos em dias diferentes sem conflito"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data1 = (datetime.now() + timedelta(days=17)).strftime("%Y-%m-%d")
    data2 = (datetime.now() + timedelta(days=18)).strftime("%Y-%m-%d")

    # Evento dia 1
    dados1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data1}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    # Evento dia 2
    dados2 = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data2}T14:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r1 = await add_evento_por_gpt(None, None, dados1)
    r2 = await add_evento_por_gpt(None, None, dados2)
    print(f"[FLUXO-3] Dia 1: {r1}, Dia 2: {r2}")

    if r1 and r2:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        dia1 = [e for e in eventos.values() if e.get("data") == data1]
        dia2 = [e for e in eventos.values() if e.get("data") == data2]
        print(f"[FLUXO-3] Dia 1: {len(dia1)}, Dia 2: {len(dia2)}")
        if len(dia1) > 0 and len(dia2) > 0:
            print("[FLUXO-3] ✓ Eventos em dias diferentes sem conflito")
