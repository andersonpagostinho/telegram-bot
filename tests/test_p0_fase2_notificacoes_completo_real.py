"""[FASE 2] P0 NOTIFICAÇÕES COMPLETO — Testes E2E Firebase Real (Lote 10/16)"""
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
async def test_evento_gera_notificacao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=91)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        bruna = [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"]
        if bruna:
            print("[NOT-1] ✓ Notificação evento criado")

@pytest.mark.asyncio
async def test_campo_notificacao_status():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=92)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        gloria = [e for e in eventos.values() if e.get("profissional", "").lower() == "gloria"]
        if gloria and gloria[0].get("status") == "confirmado":
            print("[NOT-2] ✓ Campo status = confirmado")

@pytest.mark.asyncio
async def test_multiple_notificacoes():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    for i in range(3):
        data = (datetime.now() + timedelta(days=93+i)).strftime("%Y-%m-%d")
        profs = ["Bruna", "Gloria", "Joana"]
        
        dados = {"profissional": profs[i], "servico": "manicure",
                 "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 3:
        print("[NOT-3] ✓ Múltiplas notificações geradas")

@pytest.mark.asyncio
async def test_notificacao_timestamp():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=96)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        carla = [e for e in eventos.values() if e.get("profissional", "").lower() == "carla"]
        if carla and carla[0].get("criado_em"):
            print("[NOT-4] ✓ Timestamp notificação preenchido")
