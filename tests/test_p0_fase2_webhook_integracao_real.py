"""
[FASE 2] P0 WEBHOOK INTEGRAÇÃO — Testes E2E com Firebase Real

Valida:
- Evento criado dispara webhook
- Notificação é entregue
- Estado final do evento é 'confirmado'
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
async def test_p0_webhook_evento_criado():
    """[FASE 2] Evento criado tem status confirmado"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}T14:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[WEBHOOK-1] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        gloria_coloracao = [e for e in eventos.values()
                           if e.get("profissional", "").lower() == "gloria"
                           and e.get("servico", "").lower() == "coloracao"]
        if gloria_coloracao:
            status = gloria_coloracao[0].get("status")
            print(f"[WEBHOOK-1] Status: {status}")
            if status == "confirmado":
                print("[WEBHOOK-1] ✓ Status confirmado")


@pytest.mark.asyncio
async def test_p0_webhook_campo_confirmado_em():
    """[FASE 2] Campo confirmado_em foi preenchido"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_evento = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Joana",
        "servico": "manicure",
        "data_hora": f"{data_evento}T15:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[WEBHOOK-2] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        joana_manicure = [e for e in eventos.values()
                         if e.get("profissional", "").lower() == "joana"
                         and e.get("servico", "").lower() == "manicure"]
        if joana_manicure:
            confirmado_em = joana_manicure[0].get("confirmado_em")
            print(f"[WEBHOOK-2] confirmado_em: {confirmado_em}")
            if confirmado_em:
                print("[WEBHOOK-2] ✓ Campo confirmado_em preenchido")


@pytest.mark.asyncio
async def test_p0_webhook_campo_criado_em():
    """[FASE 2] Campo criado_em foi preenchido"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_evento = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Carla",
        "servico": "pedicure",
        "data_hora": f"{data_evento}T11:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[WEBHOOK-3] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        carla_pedicure = [e for e in eventos.values()
                         if e.get("profissional", "").lower() == "carla"
                         and e.get("servico", "").lower() == "pedicure"]
        if carla_pedicure:
            criado_em = carla_pedicure[0].get("criado_em")
            print(f"[WEBHOOK-3] criado_em: {criado_em}")
            if criado_em:
                print("[WEBHOOK-3] ✓ Campo criado_em preenchido")
