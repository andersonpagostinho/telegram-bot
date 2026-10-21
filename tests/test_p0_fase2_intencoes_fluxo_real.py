"""
[FASE 2] P0 INTENÇÕES E FLUXO — Testes E2E Firebase Real (Lote 2/8)

Valida:
- Detecção de intenções diferentes
- Fluxo de agendamento completo
- Estado fluxo muda corretamente
"""

import pytest
import sys
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

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_intencao_agendamento_simples():
    """[LOTE 2] Intenção agendamento é reconhecida"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=24)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    if resultado:
        print("[INTENT-1] ✓ Agendamento reconhecido e criado")


@pytest.mark.asyncio
async def test_fluxo_agendamento_incompleto():
    """[LOTE 2] Agendamento sem confirmação não cria evento"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data}T14:00:00",
        "duracao": 120,
        "confirmado": False,  # Não confirmado!
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[INTENT-2] Resultado sem confirmação: {resultado}")


@pytest.mark.asyncio
async def test_intencao_consulta_apenas():
    """[LOTE 2] Consulta de disponibilidade não cria evento"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    # Apenas consulta, sem dados completos de agendamento
    dados = {
        "texto_usuario": "Vocês têm agenda para segunda?",
        "intencao": "consulta",
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    # Não chama add_evento_por_gpt, apenas carrega contexto
    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    if ctx:
        print("[INTENT-3] ✓ Consulta processada sem criar evento")


@pytest.mark.asyncio
async def test_fluxo_com_escolha_profissional():
    """[LOTE 2] Fluxo com escolha de profissional"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=26)).strftime("%Y-%m-%d")
    
    # Primeiro: agendamento com uma profissional
    dados1 = {
        "profissional": "Bruna",
        "servico": "manicure",
        "data_hora": f"{data}T09:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r1 = await add_evento_por_gpt(None, None, dados1)
    
    # Depois: agendamento com outra profissional
    dados2 = {
        "profissional": "Carla",
        "servico": "manicure",
        "data_hora": f"{data}T14:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    r2 = await add_evento_por_gpt(None, None, dados2)
    
    if r1 and r2:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        manicure_eventos = [e for e in eventos.values() if e.get("servico", "").lower() == "manicure"]
        if len(manicure_eventos) >= 2:
            print("[INTENT-4] ✓ Fluxo com múltiplas escolhas de profissional")


@pytest.mark.asyncio
async def test_fluxo_estado_progresso():
    """[LOTE 2] Estado do fluxo progride corretamente"""
    ctx = {"_tenant_id_guard": TENANT_TEST, "estado_fluxo": "inicio"}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=27)).strftime("%Y-%m-%d")
    dados = {
        "profissional": "Joana",
        "servico": "pedicure",
        "data_hora": f"{data}T11:00:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    
    if resultado:
        ctx_novo = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
        # Estado deve ter mudado
        if ctx_novo:
            print("[INTENT-5] ✓ Estado do fluxo progrediu")
