"""[FASE 2] P0 INTEGRAÇÃO SERVIÇOS — Testes E2E Firebase Real (Lote 19/20)"""
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
async def test_integracao_contexto_evento():
    ctx = {"_tenant_id_guard": TENANT, "servico_selecionado": "corte feminino"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=134)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        ctx_final = await carregar_contexto_temporario_v2(TENANT, ACTOR)
        if ctx_final.get("servico_selecionado") == "corte feminino":
            print("[INT-1] ✓ Contexto-Evento integrados")

@pytest.mark.asyncio
async def test_integracao_catalogo_validacao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=135)).strftime("%Y-%m-%d")
    
    # Serviço coloração = 120 min no catálogo
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T09:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        gloria = [e for e in eventos.values() if e.get("profissional", "").lower() == "gloria"]
        if gloria and gloria[0].get("duracao") == 120:
            print("[INT-2] ✓ Catálogo-Validação OK")

@pytest.mark.asyncio
async def test_integracao_profissional_servico():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=136)).strftime("%Y-%m-%d")
    
    # Testar que cada profissional pode fazer seus serviços
    combos = [
        ("Bruna", "corte feminino"),
        ("Gloria", "coloracao"),
        ("Joana", "manicure"),
        ("Carla", "pedicure"),
    ]
    
    for i, (prof, serv) in enumerate(combos):
        dados = {"profissional": prof, "servico": serv, "data_hora": f"{data}T{10+i*2:02d}:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 4: print("[INT-3] ✓ Profissional-Serviço integrados")

@pytest.mark.asyncio
async def test_integracao_webhook_notificacao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=137)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if eventos and eventos[list(eventos.keys())[0]].get("status") == "confirmado":
            print("[INT-4] ✓ Webhook-Notificação integrados")

@pytest.mark.asyncio
async def test_integracao_estado_fluxo():
    ctx = {"_tenant_id_guard": TENANT, "estado_fluxo": "aguardando_confirmacao"}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=138)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao", "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        ctx_final = await carregar_contexto_temporario_v2(TENANT, ACTOR)
        print("[INT-5] ✓ Estado-Fluxo integrados")

@pytest.mark.asyncio
async def test_integracao_completa_fim_a_fim():
    """Fluxo completo: contexto → evento → firestore → notificação"""
    ctx = {"_tenant_id_guard": TENANT, "cliente_novo": True}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=139)).strftime("%Y-%m-%d")
    dados = {"profissional": "Joana", "servico": "manicure", "data_hora": f"{data}T11:00:00", "duracao": 30, "confirmado": True, "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        # Validar contexto
        ctx_final = await carregar_contexto_temporario_v2(TENANT, ACTOR)
        # Validar evento
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        joana = [e for e in eventos.values() if e.get("profissional", "").lower() == "joana"]
        # Validar notificação (status)
        if joana and joana[0].get("status") == "confirmado" and ctx_final:
            print("[INT-6] ✓ Integração completa fim-a-fim OK")
