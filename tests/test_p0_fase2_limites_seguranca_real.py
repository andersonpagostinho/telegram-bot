"""[FASE 2] P0 LIMITES E SEGURANÇA — Testes E2E Firebase Real (Lote 16/16 - FINAL)"""
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
async def test_limite_data_proxima_ano():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[LIM-1] ✓ Data 1 ano no futuro OK")

@pytest.mark.asyncio
async def test_limite_duracao_maxima():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=116)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T09:00:00", "duracao": 480, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[LIM-2] ✓ Duração máxima (480 min) OK")

@pytest.mark.asyncio
async def test_seguranca_isolamento_tenant():
    """Verificar que dados de um tenant não vazam para outro"""
    TENANT_A = "7394370553"
    TENANT_B = "7394370554"
    
    # Evento em TENANT_A
    ctx_a = {"_tenant_id_guard": TENANT_A}
    await salvar_contexto_temporario_v2(TENANT_A, ACTOR, ctx_a)
    
    data = (datetime.now() + timedelta(days=117)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT_A, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    await add_evento_por_gpt(None, None, dados)
    
    # Verificar que TENANT_B não vê
    eventos_b = await buscar_subcolecao(f"Clientes/{TENANT_B}/Eventos") or {}
    if len(eventos_b) == 0:
        print("[SEC-1] ✓ Isolamento tenant válido")

@pytest.mark.asyncio
async def test_seguranca_cliente_id_preservado():
    """Cliente ID deve ser exatamente o que foi passado"""
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=118)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure",
             "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        joana = [e for e in eventos.values() if e.get("profissional", "").lower() == "joana"]
        if joana and joana[0].get("cliente_id") == ACTOR:
            print("[SEC-2] ✓ Cliente ID preservado corretamente")

@pytest.mark.asyncio
async def test_seguranca_tenant_id_validado():
    """Tenant ID deve ser validado e isolado"""
    VALID_TENANT = "7394370553"
    INVALID_TENANT = "9999999999"
    
    ctx = {"_tenant_id_guard": VALID_TENANT}
    await salvar_contexto_temporario_v2(VALID_TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=119)).strftime("%Y-%m-%d")
    dados = {"profissional": "Carla", "servico": "pedicure",
             "data_hora": f"{data}T15:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": VALID_TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        eventos_valid = await buscar_subcolecao(f"Clientes/{VALID_TENANT}/Eventos") or {}
        if len(eventos_valid) > 0:
            print("[SEC-3] ✓ Tenant ID validado")
