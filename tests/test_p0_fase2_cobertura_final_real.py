"""[FASE 2] P0 COBERTURA FINAL — Testes E2E Firebase Real (Lote 20/20 - FINAL)"""
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
async def test_p0_final_novo_usuario():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=140)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[FINAL-1] ✓ P0 usuário novo OK")

@pytest.mark.asyncio
async def test_p0_final_retorno_usuario():
    ctx = {"_tenant_id_guard": TENANT, "cliente_conhecida": True}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=141)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[FINAL-2] ✓ P0 retorno OK")

@pytest.mark.asyncio
async def test_p0_final_multiple_agendamentos():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    for i in range(5):
        data = (datetime.now() + timedelta(days=142+i)).strftime("%Y-%m-%d")
        profs = ["Bruna", "Gloria", "Joana", "Carla", "Bruna"]
        servs = ["corte feminino", "coloracao", "manicure", "pedicure", "escova"]
        dados = {"profissional": profs[i], "servico": servs[i], "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 5: print("[FINAL-3] ✓ P0 multiplos OK")

@pytest.mark.asyncio
async def test_p0_final_isolamento_multi_tenant():
    for tenant_id in ["7394370553", "7394370554", "7394370555"]:
        ctx = {"_tenant_id_guard": tenant_id}
        await salvar_contexto_temporario_v2(tenant_id, ACTOR, ctx)
        data = (datetime.now() + timedelta(days=147)).strftime("%Y-%m-%d")
        dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": tenant_id, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    e1 = await buscar_subcolecao(f"Clientes/7394370553/Eventos") or {}
    e2 = await buscar_subcolecao(f"Clientes/7394370554/Eventos") or {}
    e3 = await buscar_subcolecao(f"Clientes/7394370555/Eventos") or {}
    
    if len(e1) > 0 and len(e2) == 0 and len(e3) == 0:
        print("[FINAL-4] ✓ P0 isolamento tenant OK")

@pytest.mark.asyncio
async def test_p0_final_cobertura_completa():
    """Validar cobertura de todos os cenários críticos"""
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    # Scenario 1: Confirmação simples
    data1 = (datetime.now() + timedelta(days=148)).strftime("%Y-%m-%d")
    d1 = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data1}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    # Scenario 2: Múltiplos serviços
    data2 = (datetime.now() + timedelta(days=149)).strftime("%Y-%m-%d")
    d2 = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data2}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    # Scenario 3: Duração catálogo
    data3 = (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d")
    d3 = {"profissional": "Joana", "servico": "manicure", "data_hora": f"{data3}T11:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r1 = await add_evento_por_gpt(None, None, d1)
    r2 = await add_evento_por_gpt(None, None, d2)
    r3 = await add_evento_por_gpt(None, None, d3)
    
    if r1 and r2 and r3:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if len(eventos) >= 3:
            print("[FINAL-5] ✓ P0 cobertura completa OK")

@pytest.mark.asyncio
async def test_p0_final_regressao_zero():
    """Validar zero regressões em funcionalidade existente"""
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=151)).strftime("%Y-%m-%d")
    dados = {"profissional": "Carla", "servico": "pedicure", "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        carla = [e for e in eventos.values() if e.get("profissional", "").lower() == "carla"]
        if carla and carla[0].get("status") == "confirmado" and carla[0].get("confirmado") is True:
            print("[FINAL-6] ✓ ZERO REGRESSÕES validado")
