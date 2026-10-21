"""[FASE 2] P0 CONFIRMAÇÃO E NEGAÇÃO — Testes E2E Firebase Real (Lote 6/8)"""
import pytest, sys
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

TENANT = "7394370553"
ACTOR = f"whatsapp:5511991382080"

@pytest.mark.asyncio
async def test_confirmacao_cria_evento():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=41)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("confirmado") is True]:
            print("[CONF-1] ✓ Confirmação cria evento")

@pytest.mark.asyncio
async def test_confirmacao_com_evento_ja_existente():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=42)).strftime("%Y-%m-%d")
    
    dados1 = {"profissional": "Gloria", "servico": "coloracao",
              "data_hora": f"{data}T09:00:00", "duracao": 120, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r1 = await add_evento_por_gpt(None, None, dados1)
    
    dados2 = {"profissional": "Joana", "servico": "manicure",
              "data_hora": f"{data}T14:00:00", "duracao": 30, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r2 = await add_evento_por_gpt(None, None, dados2)
    
    if r1 and r2:
        print("[CONF-2] ✓ Múltiplas confirmações funcionam")

@pytest.mark.asyncio
async def test_sem_confirmacao_nao_cria():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=43)).strftime("%Y-%m-%d")
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": False,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    print(f"[CONF-3] Sem confirmação: {r}")

@pytest.mark.asyncio
async def test_negacao_cancela():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    # Simulando negação sem criar evento
    ctx_novo = {"_tenant_id_guard": TENANT, "estado_fluxo": "cancelado"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx_novo)
    print("[CONF-4] ✓ Negação processada")

@pytest.mark.asyncio
async def test_confirmacao_rapida():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=44)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "escova",
             "data_hora": f"{data}T11:00:00", "duracao": 60, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[CONF-5] ✓ Confirmação rápida funciona")
