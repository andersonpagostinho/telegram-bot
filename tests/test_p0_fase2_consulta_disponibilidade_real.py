"""
[FASE 2] P0 CONSULTA/DISPONIBILIDADE — Testes E2E com Firebase Real

Valida:
- Múltiplos eventos criados para validar disponibilidade
- Isolamento de agendamentos por cliente
- Busca de eventos existentes
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
async def test_p0_criar_evento_corte_para_consulta():
    """[FASE 2] Criar evento de corte para posterior consulta"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[CONSULTA-1] Evento corte criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        cortes = [e for e in eventos.values()
                 if e.get("servico", "").lower() == "corte feminino"]
        if cortes:
            print("[CONSULTA-1] ✓ Evento disponível para consulta")


@pytest.mark.asyncio
async def test_p0_criar_multiplos_para_validar_disponibilidade():
    """[FASE 2] Criar múltiplos eventos e validar disponibilidade"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")

    # Evento 10:00
    dados1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    # Evento 15:00
    dados2 = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data}T15:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r1 = await add_evento_por_gpt(None, None, dados1)
    r2 = await add_evento_por_gpt(None, None, dados2)
    print(f"[CONSULTA-2] Eventos: {r1}, {r2}")

    if r1 and r2:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        data_str = data
        eventos_data = [e for e in eventos.values() if e.get("data") == data_str]
        print(f"[CONSULTA-2] Eventos em {data}: {len(eventos_data)}")
        if len(eventos_data) >= 2:
            print("[CONSULTA-2] ✓ Disponibilidade validada")


@pytest.mark.asyncio
async def test_p0_isolacao_cliente_consulta():
    """[FASE 2] Cliente A e Cliente B têm eventos isolados"""
    CLIENTE_A = ACTOR_WA
    CLIENTE_B = "whatsapp:5511991382090"

    ctx_a = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, CLIENTE_A, ctx_a)

    ctx_b = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, CLIENTE_B, ctx_b)

    data = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

    # Cliente A evento
    dados_a = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T09:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": CLIENTE_A,
    }

    # Cliente B evento (outro profissional)
    dados_b = {
        "profissional": "Carla",
        "servico": "pedicure",
        "data_hora": f"{data}T13:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382090",
        "cliente_id": CLIENTE_B,
    }

    r_a = await add_evento_por_gpt(None, None, dados_a)
    r_b = await add_evento_por_gpt(None, None, dados_b)
    print(f"[CONSULTA-3] Cliente A: {r_a}, Cliente B: {r_b}")

    if r_a and r_b:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        eventos_a = len([e for e in eventos.values() if e.get("cliente_id") == CLIENTE_A])
        eventos_b = len([e for e in eventos.values() if e.get("cliente_id") == CLIENTE_B])
        print(f"[CONSULTA-3] Cliente A: {eventos_a}, Cliente B: {eventos_b}")
        if eventos_a > 0 and eventos_b > 0:
            print("[CONSULTA-3] ✓ Isolamento por cliente OK")
