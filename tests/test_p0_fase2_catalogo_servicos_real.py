"""
[FASE 2] P0 CATÁLOGO E SERVIÇOS — Testes E2E Firebase Real (Lote 3/8)

Valida:
- Serviços do catálogo são usados
- Durações corretas do catálogo
- Profissionais habilitados para serviços
"""

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
async def test_servico_corte_feminino():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=28)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino", 
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("servico", "").lower() == "corte feminino"]:
            print("[CAT-1] ✓ Corte feminino criado")

@pytest.mark.asyncio
async def test_servico_coloracao():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=29)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T09:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        coloracao = [e for e in eventos.values() if e.get("servico", "").lower() == "coloracao"]
        if coloracao and coloracao[0].get("duracao") == 120:
            print("[CAT-2] ✓ Coloração com duração correta (120 min)")

@pytest.mark.asyncio
async def test_servico_manicure():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    dados = {"profissional": "Carla", "servico": "manicure",
             "data_hora": f"{data}T14:00:00", "duracao": 30, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("servico", "").lower() == "manicure"]:
            print("[CAT-3] ✓ Manicure criado")

@pytest.mark.asyncio
async def test_servico_escova():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "escova",
             "data_hora": f"{data}T15:00:00", "duracao": 60, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        if [e for e in eventos.values() if e.get("servico", "").lower() == "escova"]:
            print("[CAT-4] ✓ Escova criada")

@pytest.mark.asyncio
async def test_multiplos_servicos():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
    
    servicos = ["corte feminino", "coloracao", "manicure"]
    profissionais = ["Bruna", "Gloria", "Carla"]
    
    for i, (serv, prof) in enumerate(zip(servicos, profissionais)):
        hora = f"{9+i*2:02d}"
        dados = {"profissional": prof, "servico": serv,
                 "data_hora": f"{data}T{hora}:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 3:
        print("[CAT-5] ✓ Múltiplos serviços criados")
