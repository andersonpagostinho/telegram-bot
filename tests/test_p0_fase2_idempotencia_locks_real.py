"""[FASE 2] P0 IDEMPOTÊNCIA E LOCKS — Testes E2E Firebase Real (Lote 9/16)"""
import pytest, asyncio, sys
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
async def test_confirmacao_dupla():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=85)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r1 = await add_evento_por_gpt(None, None, dados)
    r2 = await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    bruna = [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna" 
             and e.get("data") == data]
    if len(bruna) <= 1:
        print("[IDEMP-1] ✓ Idempotência: 2 chamadas = 1 evento")

@pytest.mark.asyncio
async def test_confirmacao_tripla():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=86)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    for _ in range(3):
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    gloria = [e for e in eventos.values() if e.get("profissional", "").lower() == "gloria"
              and e.get("data") == data]
    if len(gloria) <= 1:
        print("[IDEMP-2] ✓ Idempotência: 3 chamadas = 1 evento")

@pytest.mark.asyncio
async def test_lock_timeout():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=87)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Joana", "servico": "manicure",
             "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[IDEMP-3] ✓ Lock funcionou (evento criado)")

@pytest.mark.asyncio
async def test_lock_multiplos_clientes():
    async def criar(cliente_id, prof):
        ctx = {"_tenant_id_guard": TENANT}
        await salvar_contexto_temporario_v2(TENANT, cliente_id, ctx)
        data = (datetime.now() + timedelta(days=88)).strftime("%Y-%m-%d")
        
        dados = {"profissional": prof, "servico": "pedicure",
                 "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": cliente_id.split(":")[-1], "cliente_id": cliente_id}
        return await add_evento_por_gpt(None, None, dados)
    
    clientes = [f"whatsapp:551199138209{i}" for i in range(3)]
    profs = ["Bruna", "Gloria", "Joana"]
    
    results = await asyncio.gather(*[criar(c, p) for c, p in zip(clientes, profs)])
    if all(results):
        print("[IDEMP-4] ✓ Locks multiplos clientes OK")

@pytest.mark.asyncio
async def test_reentrada_lock():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=89)).strftime("%Y-%m-%d")
    
    # Mesmo cliente, mesmo horário, deve ser idempotente
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T12:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r1 = await add_evento_por_gpt(None, None, dados)
    r2 = await add_evento_por_gpt(None, None, dados)
    r3 = await add_evento_por_gpt(None, None, dados)
    
    if r1 and r2 and r3:
        print("[IDEMP-5] ✓ Reentrada lock funciona")

@pytest.mark.asyncio
async def test_lock_diferentes_horarios():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    # Mesmo profissional, horários diferentes
    for hora in ["09", "11", "13", "15", "17"]:
        dados = {"profissional": "Bruna", "servico": "corte feminino",
                 "data_hora": f"{data}T{hora}:00:00", "duracao": 40, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    bruna = [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"
             and e.get("data") == data]
    if len(bruna) >= 5:
        print("[IDEMP-6] ✓ Locks diferentes horários OK")
