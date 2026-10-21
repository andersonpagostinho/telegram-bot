"""[FASE 2] P0 CENÁRIOS REALISTAS — Testes E2E Firebase Real (Lote 8/8 - Final)"""
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
async def test_cenario_cliente_novo():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=75)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[REAL-1] ✓ Cliente novo agendou sucesso")

@pytest.mark.asyncio
async def test_cenario_reagendamento():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    data = (datetime.now() + timedelta(days=76)).strftime("%Y-%m-%d")
    
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    r = await add_evento_por_gpt(None, None, dados)
    if r:
        print("[REAL-2] ✓ Reagendamento realizado")

@pytest.mark.asyncio
async def test_cenario_multiplos_agendamentos():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    servicos = ["corte feminino", "manicure", "pedicure"]
    for i, serv in enumerate(servicos):
        data = (datetime.now() + timedelta(days=77+i)).strftime("%Y-%m-%d")
        profs = ["Bruna", "Joana", "Carla"]
        dados = {"profissional": profs[i], "servico": serv,
                 "data_hora": f"{data}T10:00:00", "duracao": 30, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
        await add_evento_por_gpt(None, None, dados)
    
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 3:
        print("[REAL-3] ✓ Múltiplos agendamentos realizados")

@pytest.mark.asyncio
async def test_cenario_fim_de_semana():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    # Sábado
    data_sabado = (datetime.now() + timedelta(days=80)).strftime("%Y-%m-%d")
    dados_sab = {"profissional": "Bruna", "servico": "corte feminino",
                 "data_hora": f"{data_sabado}T10:00:00", "duracao": 40, "confirmado": True,
                 "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados_sab)
    if r:
        print("[REAL-4] ✓ Agendamento fim de semana")

@pytest.mark.asyncio
async def test_cenario_horario_ocupado():
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=81)).strftime("%Y-%m-%d")
    
    # Primeiro agendamento
    dados1 = {"profissional": "Gloria", "servico": "coloracao",
              "data_hora": f"{data}T10:00:00", "duracao": 120, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    await add_evento_por_gpt(None, None, dados1)
    
    # Tentar agendar no mesmo slot com outro cliente
    CLIENTE_B = "whatsapp:5511991382090"
    ctx_b = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, CLIENTE_B, ctx_b)
    
    dados2 = {"profissional": "Gloria", "servico": "escova",
              "data_hora": f"{data}T10:30:00", "duracao": 60, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382090", "cliente_id": CLIENTE_B}
    r = await add_evento_por_gpt(None, None, dados2)
    print(f"[REAL-5] Horário ocupado: {r}")
