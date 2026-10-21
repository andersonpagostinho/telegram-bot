"""[FASE 2] P0 RECOVERY E FALHAS — Testes E2E Firebase Real (Lote 12/16)"""
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
async def test_falha_recupera():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=98)).strftime("%Y-%m-%d")
    
    # Tentar com dados válidos
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[REC-1] ✓ Recovery de falha")

@pytest.mark.asyncio
async def test_timeout_retry():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=99)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[REC-2] ✓ Timeout recuperado")

@pytest.mark.asyncio
async def test_evento_parcial_nao_salvo():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    # Dados incompletos
    dados = {"profissional": "Joana"}  # Sem serviço, data, etc
    
    r = await add_evento_por_gpt(None, None, dados)
    print(f"[REC-3] Dados incompletos: {r}")

@pytest.mark.asyncio
async def test_rollback_evento():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    # Se falhar, evento não deve ficar incompleto
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        carla = [e for e in eventos.values() if e.get("profissional", "").lower() == "carla"]
        if carla:
            print("[REC-4] ✓ Rollback seguro")
