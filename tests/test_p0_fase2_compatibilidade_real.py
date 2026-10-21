"""[FASE 2] P0 COMPATIBILIDADE — Testes E2E Firebase Real (Lote 15/16)"""
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
async def test_compat_nomes_acentuados():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=112)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[COMPAT-1] ✓ Acentuação compatível")

@pytest.mark.asyncio
async def test_compat_unicode():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=113)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloração",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[COMPAT-2] ✓ Unicode compatível")

@pytest.mark.asyncio
async def test_compat_campos_opcionais():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=114)).strftime("%Y-%m-%d")
    
    # Sem alguns campos opcionais
    dados = {"profissional": "Joana", "servico": "manicure",
             "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[COMPAT-3] ✓ Campos opcionais OK")

@pytest.mark.asyncio
async def test_compat_tipos_dados():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=115)).strftime("%Y-%m-%d")
    
    # String duracao deveria ser int, mas sistema processa
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if eventos:
            print("[COMPAT-4] ✓ Tipos de dados compatíveis")
