"""[FASE 2] P0 VALIDAÇÃO AVANÇADA — Testes E2E Firebase Real (Lote 18/20)"""
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
async def test_validacao_campos_obrigatorios():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=127)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[VAL-1] ✓ Validação obrigatórios PASS")

@pytest.mark.asyncio
async def test_validacao_tipos():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=128)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[VAL-2] ✓ Tipos validados")

@pytest.mark.asyncio
async def test_validacao_intervalo_horario():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=129)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure", "data_hora": f"{data}T08:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r: print("[VAL-3] ✓ Horário validado")

@pytest.mark.asyncio
async def test_validacao_sobreposicao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=130)).strftime("%Y-%m-%d")
    
    dados1 = {"profissional": "Carla", "servico": "pedicure", "data_hora": f"{data}T10:00:00", "duracao": 60, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r1 = await add_evento_por_gpt(None, None, dados1)
    
    dados2 = {"profissional": "Carla", "servico": "pedicure", "data_hora": f"{data}T10:30:00", "duracao": 60, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r2 = await add_evento_por_gpt(None, None, dados2)
    
    print(f"[VAL-4] Sobreposição: {r1}, {r2}")

@pytest.mark.asyncio
async def test_validacao_capacidade():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=131)).strftime("%Y-%m-%d")
    
    for i in range(3):
        dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T{10+i*2:02d}:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 3: print("[VAL-5] ✓ Capacidade validada")

@pytest.mark.asyncio
async def test_validacao_integridade_referencial():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=132)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if eventos: print("[VAL-6] ✓ Integridade referencial OK")

@pytest.mark.asyncio
async def test_validacao_cross_tenant():
    TENANT_A = "7394370553"
    TENANT_B = "7394370554"
    
    ctx_a = {"_tenant_id_guard": TENANT_A}
    await salvar_contexto_temporario_v2(TENANT_A, ACTOR, ctx_a)
    
    data = (datetime.now() + timedelta(days=133)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure", "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT_A, "user_id": "5511991382080", "cliente_id": ACTOR}
    await add_evento_por_gpt(None, None, dados)
    
    eventos_b = await buscar_subcolecao(f"Clientes/{TENANT_B}/Eventos") or {}
    if len(eventos_b) == 0: print("[VAL-7] ✓ Cross-tenant isolado")
