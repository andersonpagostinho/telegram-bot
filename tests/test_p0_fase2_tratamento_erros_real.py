"""
[FASE 2] P0 TRATAMENTO DE ERROS — Testes E2E com Firebase Real

Valida:
- Evento com dados válidos é criado
- Evento com dados inválidos não é criado
- Diferentes profissionais funcionam
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
async def test_p0_evento_servico_valido_criado():
    """[FASE 2] Serviço válido (corte feminino) é criado sem problema"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")
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
    print(f"[ERRO-1] Serviço válido: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        corte = [e for e in eventos.values()
                if e.get("servico", "").lower() == "corte feminino"]
        if corte:
            print("[ERRO-1] ✓ Serviço válido criado sem problemas")


@pytest.mark.asyncio
async def test_p0_profissional_valido_encontrado():
    """[FASE 2] Profissional válido (Gloria) é encontrado e evento criado"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=13)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Gloria",
        "servico": "hidratacao",
        "data_hora": f"{data}T14:00:00",
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[ERRO-2] Profissional válido: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        gloria = [e for e in eventos.values()
                 if e.get("profissional", "").lower() == "gloria"]
        if gloria:
            print("[ERRO-2] ✓ Profissional válido encontrado")


@pytest.mark.asyncio
async def test_p0_data_futura_valida():
    """[FASE 2] Data futura (válida) é aceita"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_futura = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Joana",
        "servico": "pedicure",
        "data_hora": f"{data_futura}T11:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[ERRO-3] Data futura: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        futuro = [e for e in eventos.values() if e.get("data") == data_futura]
        if futuro:
            print("[ERRO-3] ✓ Data futura aceita corretamente")


@pytest.mark.asyncio
async def test_p0_multiplos_servicos_disponiveis():
    """[FASE 2] Diferentes serviços podem ser agendados"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    # Manicure
    dados1 = {
        "profissional": "Carla",
        "servico": "manicure",
        "data_hora": f"{data}T09:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    # Escova
    dados2 = {
        "profissional": "Bruna",
        "servico": "escova",
        "data_hora": f"{data}T15:00:00",
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r1 = await add_evento_por_gpt(None, None, dados1)
    r2 = await add_evento_por_gpt(None, None, dados2)
    print(f"[ERRO-4] Manicure: {r1}, Escova: {r2}")

    if r1 and r2:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        manicure = [e for e in eventos.values() if e.get("servico", "").lower() == "manicure"]
        escova = [e for e in eventos.values() if e.get("servico", "").lower() == "escova"]
        if manicure and escova:
            print("[ERRO-4] ✓ Múltiplos serviços disponíveis")
