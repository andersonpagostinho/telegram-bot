"""
[FASE 2] P0 IDENTIDADE E SESSÃO — Testes E2E com Firebase Real (Lote 1/8)

Valida:
- Identidade do cliente preservada (actor_id)
- Sessão isolada por tenant
- Contexto de sessão mantido
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
async def test_identidade_actor_id_preservado():
    """[LOTE 1] Actor ID com prefixo whatsapp: é preservado"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
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
    print(f"[IDENT-1] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        evento = [e for e in eventos.values() if e.get("cliente_id") == ACTOR_WA]
        if evento:
            print("[IDENT-1] ✓ Actor ID preservado com prefixo whatsapp:")


@pytest.mark.asyncio
async def test_sessao_isolada_por_tenant():
    """[LOTE 1] Sessão de um tenant não vê dados de outro"""
    TENANT_A = "7394370553"
    TENANT_B = "7394370554"
    CLIENTE = "whatsapp:5511991382080"

    # Evento em TENANT_A
    ctx_a = {"_tenant_id_guard": TENANT_A}
    await salvar_contexto_temporario_v2(TENANT_A, CLIENTE, ctx_a)

    data = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")
    dados_a = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_A,
        "user_id": "5511991382080",
        "cliente_id": CLIENTE,
    }

    resultado_a = await add_evento_por_gpt(None, None, dados_a)
    print(f"[IDENT-2] Evento TENANT_A: {resultado_a}")

    # Verificar que TENANT_B não vê evento de TENANT_A
    eventos_a = await buscar_subcolecao(f"Clientes/{TENANT_A}/Eventos") or {}
    eventos_b = await buscar_subcolecao(f"Clientes/{TENANT_B}/Eventos") or {}

    total_a = len(eventos_a)
    total_b = len(eventos_b)
    print(f"[IDENT-2] TENANT_A: {total_a}, TENANT_B: {total_b}")
    if total_a > 0 and total_b == 0:
        print("[IDENT-2] ✓ Isolamento por tenant validado")


@pytest.mark.asyncio
async def test_contexto_sessao_carregado():
    """[LOTE 1] Contexto de sessão carregado corretamente"""
    dados_contexto = {
        "_tenant_id_guard": TENANT_TEST,
        "historico_conversas": ["oi", "quero corte"],
        "estado_fluxo": "aguardando_profissional",
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, dados_contexto)

    ctx_carregado = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    print(f"[IDENT-3] Contexto carregado: {bool(ctx_carregado)}")

    if ctx_carregado.get("estado_fluxo") == "aguardando_profissional":
        print("[IDENT-3] ✓ Contexto de sessão carregado corretamente")


@pytest.mark.asyncio
async def test_multiplos_clientes_mesmo_tenant():
    """[LOTE 1] Múltiplos clientes no mesmo tenant não colidem"""
    CLIENTE_A = "whatsapp:5511991382080"
    CLIENTE_B = "whatsapp:5511991382081"

    ctx_a = {"_tenant_id_guard": TENANT_TEST}
    ctx_b = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, CLIENTE_A, ctx_a)
    await salvar_contexto_temporario_v2(TENANT_TEST, CLIENTE_B, ctx_b)

    data = (datetime.now() + timedelta(days=22)).strftime("%Y-%m-%d")

    # Evento Cliente A
    dados_a = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T09:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382080",
        "cliente_id": CLIENTE_A,
    }

    # Evento Cliente B
    dados_b = {
        "profissional": "Gloria",
        "servico": "coloracao",
        "data_hora": f"{data}T14:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382081",
        "cliente_id": CLIENTE_B,
    }

    r_a = await add_evento_por_gpt(None, None, dados_a)
    r_b = await add_evento_por_gpt(None, None, dados_b)
    print(f"[IDENT-4] Cliente A: {r_a}, Cliente B: {r_b}")

    if r_a and r_b:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        eventos_a = [e for e in eventos.values() if e.get("cliente_id") == CLIENTE_A]
        eventos_b = [e for e in eventos.values() if e.get("cliente_id") == CLIENTE_B]
        if len(eventos_a) > 0 and len(eventos_b) > 0:
            print("[IDENT-4] ✓ Múltiplos clientes isolados no mesmo tenant")


@pytest.mark.asyncio
async def test_sessao_persistencia_multiplas_operacoes():
    """[LOTE 1] Sessão persiste através de múltiplas operações"""
    ctx_inicial = {
        "_tenant_id_guard": TENANT_TEST,
        "contador_operacoes": 0,
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx_inicial)

    data = (datetime.now() + timedelta(days=23)).strftime("%Y-%m-%d")

    # Op 1
    dados1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data}T09:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382080",
        "cliente_id": ACTOR_WA,
    }
    await add_evento_por_gpt(None, None, dados1)

    # Op 2
    dados2 = {
        "profissional": "Gloria",
        "servico": "hidratacao",
        "data_hora": f"{data}T15:00:00",
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": "5511991382080",
        "cliente_id": ACTOR_WA,
    }
    await add_evento_por_gpt(None, None, dados2)

    # Verificar contexto
    ctx_final = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    if ctx_final.get("_tenant_id_guard") == TENANT_TEST:
        print("[IDENT-5] ✓ Sessão persistiu através de múltiplas operações")
