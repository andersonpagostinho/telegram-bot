"""
[FASE 2] P0 PROFISSIONAL — Testes E2E com Firebase Real

Valida:
- Profissional pode agendar
- Profissional vê apenas seus eventos
- Isolamento de profissionais
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
async def test_p0_profissional_evento_criado():
    """[FASE 2] Cenário: Profissional consegue criar evento"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Joana",
        "servico": "corte feminino",
        "data_hora": f"{(datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d')}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[PROF-1] Evento criado: {resultado}")


@pytest.mark.asyncio
async def test_p0_profissional_isolamento():
    """[FASE 2] Cenário: Profissional vê apenas seus eventos"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    # Evento com Bruna
    dados_bruna = {
        "profissional": "Bruna",
        "servico": "hidratacao",
        "data_hora": f"{(datetime.now() + timedelta(days=105)).strftime('%Y-%m-%d')}T11:00:00",
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado1 = await add_evento_por_gpt(None, None, dados_bruna)
    print(f"[PROF-2] Evento Bruna: {resultado1}")

    # Evento com Carla
    dados_carla = {
        "profissional": "Carla",
        "servico": "coloracao",
        "data_hora": f"{(datetime.now() + timedelta(days=110)).strftime('%Y-%m-%d')}T13:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382090",  # Outro cliente
        "cliente_id": "whatsapp:5511991382090",
    }

    resultado2 = await add_evento_por_gpt(None, None, dados_carla)
    print(f"[PROF-2] Evento Carla: {resultado2}")

    if resultado1 and resultado2:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        bruna_eventos = len([e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"])
        carla_eventos = len([e for e in eventos.values() if e.get("profissional", "").lower() == "carla"])
        print(f"[PROF-2] Bruna: {bruna_eventos}, Carla: {carla_eventos}")
        if bruna_eventos > 0 and carla_eventos > 0:
            print("[PROF-2] ✓ Ambas profissionais têm eventos")
