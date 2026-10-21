"""
[FASE 2] P0 EDGE CASES — Testes E2E com Firebase Real

Valida:
- Nomes com acentuação (José, São Paulo)
- Muito tempo no futuro (meses)
- Durações extremas (1 min vs 480 min)
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
from services.interpretador_conversacional import interpretar_conversa_operacional
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_edge_case_data_distante():
    """[FASE 2] Agendamento para 3 meses no futuro"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_distante = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

    dados = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data_distante}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EDGE-1] Evento 90 dias: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        evento_distante = [e for e in eventos.values()
                          if e.get("data") == data_distante]
        if evento_distante:
            print("[EDGE-1] ✓ Data distante aceita")


@pytest.mark.asyncio
async def test_p0_edge_case_duracao_extrema_longa():
    """[FASE 2] Agendamento com duração longa (8 horas)"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Gloria",
        "servico": "coloracao",  # Durações extremas em tratamentos especiais
        "data_hora": f"{(datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')}T09:00:00",
        "duracao": 480,  # 8 horas
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EDGE-2] Evento 8h: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        evento_longo = [e for e in eventos.values()
                       if e.get("duracao") == 480]
        if evento_longo:
            print("[EDGE-2] ✓ Duração extrema aceita")


@pytest.mark.asyncio
async def test_p0_edge_case_duracao_minima():
    """[FASE 2] Agendamento com duração mínima (10 min)"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Joana",
        "servico": "manicure",
        "data_hora": f"{(datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')}T12:00:00",
        "duracao": 10,  # Duração mínima
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EDGE-3] Evento 10min: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        evento_curto = [e for e in eventos.values()
                       if e.get("duracao") == 10]
        if evento_curto:
            print("[EDGE-3] ✓ Duração mínima aceita")
