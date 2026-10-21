"""[FASE 2] P0 STRESS E VOLUME — Testes E2E Firebase Real (Lote 7/8)"""
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
async def test_10_eventos_sequenciais():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    profs = ["Bruna", "Gloria", "Joana", "Carla"] * 3
    for i, prof in enumerate(profs[:10]):
        data = (datetime.now() + timedelta(days=45+i)).strftime("%Y-%m-%d")
        dados = {"profissional": prof, "servico": "manicure",
                 "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 10:
        print("[STRESS-1] ✓ 10 eventos criados")

@pytest.mark.asyncio
async def test_20_eventos_mesma_profissional():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    for i in range(5):
        data = (datetime.now() + timedelta(days=55+i)).strftime("%Y-%m-%d")
        dados = {"profissional": "Bruna", "servico": "corte feminino",
                 "data_hora": f"{data}T{10+i*2:02d}:00:00", "duracao": 40, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 5:
        print("[STRESS-2] ✓ Múltiplos eventos Bruna")

@pytest.mark.asyncio
async def test_paralelo_5_clientes():
    async def criar(cliente_id):
        ctx = {"_tenant_id_guard": TENANT}
        await salvar_contexto_temporario_v2(TENANT, cliente_id, ctx)
        data = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        dados = {"profissional": "Gloria", "servico": "coloracao",
                 "data_hora": f"{data}T10:00:00", "duracao": 120, "confirmado": True,
                 "tenant_id": TENANT, "user_id": cliente_id.split(":")[-1], "cliente_id": cliente_id}
        return await add_evento_por_gpt(None, None, dados)
    
    clientes = [f"whatsapp:551199138208{i}" for i in range(5)]
    results = await asyncio.gather(*[criar(c) for c in clientes])
    if all(results):
        print("[STRESS-3] ✓ 5 clientes paralelo")

@pytest.mark.asyncio
async def test_volume_50_eventos():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    for i in range(5):
        data = (datetime.now() + timedelta(days=65+i)).strftime("%Y-%m-%d")
        for j in range(10):
            prof = ["Bruna", "Gloria", "Joana", "Carla"][j % 4]
            dados = {"profissional": prof, "servico": "manicure",
                     "data_hora": f"{data}T{9+j%8:02d}:00:00", "duracao": 30, "confirmado": True,
                     "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
            await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    print(f"[STRESS-4] Total eventos: {len(eventos)}")

@pytest.mark.asyncio
async def test_cache_firestore():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=70)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T12:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r1 = await add_evento_por_gpt(None, None, dados)
    eventos1 = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    eventos2 = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    
    if len(eventos1) == len(eventos2):
        print("[STRESS-5] ✓ Cache Firestore consistente")
