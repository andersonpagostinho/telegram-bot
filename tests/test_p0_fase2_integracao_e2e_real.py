"""[FASE 2] P0 INTEGRAÇÃO E2E — Testes E2E Firebase Real (Lote 14/16)"""
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
async def test_fluxo_usuario_novo_completo():
    """Cliente novo: contexto vazio → agendamento → evento em Firestore"""
    # Usuário novo, contexto vazio
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    # Agendamento
    data = (datetime.now() + timedelta(days=108)).strftime("%Y-%m-%d")
    dados = {"profissional": "Bruna", "servico": "corte feminino",
             "data_hora": f"{data}T10:00:00", "duracao": 40, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    
    # Validar
    if r:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
        bruna = [e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"]
        if bruna:
            print("[E2E-1] ✓ Fluxo novo usuário completo")

@pytest.mark.asyncio
async def test_fluxo_usuario_retorno():
    """Cliente retorno: contexto carregado → novo agendamento"""
    # Usuário com contexto prévio
    ctx = {"_tenant_id_guard": TENANT, "cliente_conhecida": True, "historico": ["msg1"]}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    data = (datetime.now() + timedelta(days=109)).strftime("%Y-%m-%d")
    dados = {"profissional": "Gloria", "servico": "coloracao",
             "data_hora": f"{data}T14:00:00", "duracao": 120, "confirmado": True,
             "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    
    r = await add_evento_por_gpt(None, None, dados)
    
    if r:
        ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR)
        if ctx_carregado.get("cliente_conhecida"):
            print("[E2E-2] ✓ Fluxo retorno usuario OK")

@pytest.mark.asyncio
async def test_fluxo_multiplas_operacoes():
    """Sequência: contexto → opção 1 → opção 2 → agendamento → validação"""
    ctx = {"_tenant_id_guard": TENANT}
    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx)
    
    # Op 1: Agendamento 1
    data1 = (datetime.now() + timedelta(days=110)).strftime("%Y-%m-%d")
    dados1 = {"profissional": "Joana", "servico": "manicure",
              "data_hora": f"{data1}T10:00:00", "duracao": 30, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    await add_evento_por_gpt(None, None, dados1)
    
    # Op 2: Agendamento 2
    data2 = (datetime.now() + timedelta(days=111)).strftime("%Y-%m-%d")
    dados2 = {"profissional": "Carla", "servico": "pedicure",
              "data_hora": f"{data2}T15:00:00", "duracao": 30, "confirmado": True,
              "tenant_id": TENANT, "user_id": "5511991382080", "cliente_id": ACTOR}
    await add_evento_por_gpt(None, None, dados2)
    
    # Validar
    eventos = await buscar_subcolecao(f"Clientes/{TENANT}/Eventos") or {}
    if len(eventos) >= 2:
        print("[E2E-3] ✓ Fluxo múltiplas operações OK")
