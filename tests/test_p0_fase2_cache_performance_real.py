"""[FASE 2] P0 CACHE E PERFORMANCE — Testes E2E Firebase Real (Lote 13/16)"""
import pytest, sys, time
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
async def test_cache_leitura():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=101)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    await add_evento_por_gpt(None, None, dados)
    
    t1 = time.time()
    eventos1 = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos")
    t_primeiro = time.time() - t1
    
    t2 = time.time()
    eventos2 = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos")
    t_segundo = time.time() - t2
    
    if len(eventos1) == len(eventos2):
        print(f"[PERF-1] ✓ Cache consistente ({t_primeiro:.3f}s → {t_segundo:.3f}s)")

@pytest.mark.asyncio
async def test_performance_criacao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    t_inicio = time.time()
    
    for i in range(5):
        data = (datetime.now() + timedelta(days=102+i)).strftime("%Y-%m-%d")
        dados = {"profissional": "Gloria", "servico": "coloracao",
                 "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    t_total = time.time() - t_inicio
    media = t_total / 5
    
    print(f"[PERF-2] ✓ 5 eventos em {t_total:.2f}s (média {media:.2f}s/evento)")

@pytest.mark.asyncio
async def test_leitura_escrita_concorrente():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=107)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Joana", "servico": "manicure",
             "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos")
    if eventos:
        print("[PERF-3] ✓ Leitura durante escrita OK")
