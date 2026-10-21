"""[FASE 2] P0 PROFISSIONAIS — Testes E2E Firebase Real (Lote 4/8)"""
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
async def test_prof_bruna():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"]:
            print("[PROF-1] ✓ Bruna criou evento")

@pytest.mark.asyncio
async def test_prof_gloria():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=34)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T09:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("profissional", "").lower() == "gloria"]:
            print("[PROF-2] ✓ Gloria criou evento")

@pytest.mark.asyncio
async def test_prof_joana():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure",
             "data_hora": f"{data}T14:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("profissional", "").lower() == "joana"]:
            print("[PROF-3] ✓ Joana criou evento")

@pytest.mark.asyncio
async def test_prof_carla():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=36)).strftime("%Y-%m-%d")
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("profissional", "").lower() == "carla"]:
            print("[PROF-4] ✓ Carla criou evento")

@pytest.mark.asyncio
async def test_multiplos_profissionais():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")
    
    profs = ["Bruna", "Gloria", "Joana", "Carla"]
    servs = ["corte feminino", "coloracao", "manicure", "pedicure"]
    
    for prof, serv in zip(profs, servs):
        dados = {"profissional": prof, "servico": serv,
                 "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 4:
        print("[PROF-5] ✓ Todas profissionais criaram eventos")
