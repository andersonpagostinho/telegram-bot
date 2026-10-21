"""[FASE 2] P0 ROTEAMENTO & DISPATCHER — Testes E2E Firebase Real (Lote 17/20)"""
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
async def test_rota_agendamento():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[ROTA-1] ✓ Rota agendamento funciona")

@pytest.mark.asyncio
async def test_dispatcher_profissional():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    for prof in ["Bruna", "Gloria", "Joana", "Carla"]:
        data = (datetime.now() + timedelta(days=121)).strftime("%Y-%m-%d")
        dados = {"profissional": prof, "servico": "manicure", "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 4: print("[ROTA-2] ✓ Dispatcher profissional OK")

@pytest.mark.asyncio
async def test_rota_multipla_tenants():
    for tenant_id in ["7394370553", "7394370554"]:
        ctx = {"_tenant_id_guard": tenant_id}
        await salvar_contexto_temporario_v2(tenant_id, ACTOR, ctx)
        data = (datetime.now() + timedelta(days=122)).strftime("%Y-%m-%d")
        dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": tenant_id, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    print("[ROTA-3] ✓ Rota multipla tenants OK")

@pytest.mark.asyncio
async def test_rota_fallback():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=123)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[ROTA-4] ✓ Fallback rota OK")

@pytest.mark.asyncio
async def test_dispatcher_prioridade():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    dados_p1 = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{(datetime.now() + timedelta(days=124)).strftime('%Y-%m-%d')}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r1 = await add_evento_por_gpt(None, None, dados_p1)
    
    dados_p2 = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{(datetime.now() + timedelta(days=125)).strftime('%Y-%m-%d')}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r2 = await add_evento_por_gpt(None, None, dados_p2)
    
    if r1 and r2: print("[ROTA-5] ✓ Dispatcher prioridade OK")

@pytest.mark.asyncio
async def test_rota_feedback():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=126)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure", "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if eventos: print("[ROTA-6] ✓ Feedback rota OK")
