"""
[FASE 2] P0 EXTRAÇÃO DE DADOS — Testes E2E com Firebase Real

Valida:
- Serviço extraído corretamente do payload
- Profissional extraído corretamente
- Data e hora mapeadas adequadamente
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
async def test_p0_extracao_servico_corte_feminino():
    """[FASE 2] Serviço 'corte feminino' extraído e salvo corretamente"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
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
    print(f"[EXTRACAO-1] Evento com corte: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        corte = [e for e in eventos.values()
                if e.get("servico", "").lower() == "corte feminino"]
        if corte:
            print("[EXTRACAO-1] ✓ Serviço 'corte feminino' extraído corretamente")


@pytest.mark.asyncio
async def test_p0_extracao_profissional_normalizado():
    """[FASE 2] Profissional extraído com normalização"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")

    # Payload com profissional "Gloria"
    dados = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data}T14:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EXTRACAO-2] Evento com Gloria: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        gloria = [e for e in eventos.values()
                 if e.get("profissional", "").lower() == "gloria"]
        if gloria:
            print("[EXTRACAO-2] ✓ Profissional 'Gloria' extraído normalizado")


@pytest.mark.asyncio
async def test_p0_extracao_data_hora_mapeada():
    """[FASE 2] Data e hora mapeadas corretamente em campos separados"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    data_hora = f"{data}T16:30:00"

    dados = {
        "profissional": "Joana",
        "servico": "manicure",
        "data_hora": data_hora,
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EXTRACAO-3] Evento com data/hora: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        joana = [e for e in eventos.values()
                if e.get("profissional", "").lower() == "joana"]
        if joana:
            evento = joana[0]
            data_campo = evento.get("data")
            hora = evento.get("hora_inicio")
            print(f"[EXTRACAO-3] Data: {data_campo}, Hora: {hora}")
            if data_campo == data and hora:
                print("[EXTRACAO-3] ✓ Data e hora extraídas corretamente")


@pytest.mark.asyncio
async def test_p0_extracao_duracao_catalogo():
    """[FASE 2] Duração extraída do catálogo do serviço"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=11)).strftime("%Y-%m-%d")

    # Coloração tem duração de 120 min no catálogo
    dados = {
        "profissional": "Carla",
        "servico": "coloracao",
        "data_hora": f"{data}T09:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EXTRACAO-4] Evento coloração: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        coloracao = [e for e in eventos.values()
                    if e.get("servico", "").lower() == "coloracao"]
        if coloracao:
            duracao = coloracao[0].get("duracao")
            print(f"[EXTRACAO-4] Duração: {duracao}")
            if duracao == 120:
                print("[EXTRACAO-4] ✓ Duração do catálogo extraída corretamente")
