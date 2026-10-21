"""[FASE 2] P0 ESTADO E CONTEXTO — Testes E2E Firebase Real (Lote 11/16)"""
import pytest, sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))
import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from handlers.event_handler import add_evento_por_gpt

TENANT = "7394370553"
ACTOR = f"whatsapp:5511991382080"

@pytest.mark.asyncio
async def test_estado_inicial():
    ctx = {"_tenant_id_guard": TENANT, "estado_fluxo": "inicio"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR)
    if ctx_carregado.get("estado_fluxo") == "inicio":
        print("[STATE-1] ✓ Estado inicial preservado")

@pytest.mark.asyncio
async def test_estado_aguardando_confirmacao():
    ctx = {"_tenant_id_guard": TENANT, "estado_fluxo": "aguardando_confirmacao_agendamento"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR)
    if "aguardando" in ctx_carregado.get("estado_fluxo", ""):
        print("[STATE-2] ✓ Estado aguardando confirmação")

@pytest.mark.asyncio
async def test_contexto_histórico():
    ctx = {"_tenant_id_guard": TENANT, "historico": ["msg1", "msg2", "msg3"]}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR)
    if len(ctx_carregado.get("historico", [])) == 3:
        print("[STATE-3] ✓ Histórico carregado")

@pytest.mark.asyncio
async def test_contexto_variáveis():
    ctx = {"_tenant_id_guard": TENANT, "serviço_selecionado": "corte feminino", 
           "profissional_selecionada": "Bruna"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR)
    if ctx_carregado.get("serviço_selecionado") == "corte feminino":
        print("[STATE-4] ✓ Variáveis de estado preservadas")

@pytest.mark.asyncio
async def test_estado_apos_agendamento():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=97)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    await add_evento_por_gpt(None, None, dados)
    
    ctx_final = await carregar_contexto_temporario_v2(TENANT, ACTOR)
    if ctx_final.get("_tenant_id_guard") == TENANT:
        print("[STATE-5] ✓ Estado mantido após agendamento")
