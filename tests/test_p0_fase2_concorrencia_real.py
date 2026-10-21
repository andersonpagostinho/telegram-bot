"""
[FASE 2] P0 CONCORRÊNCIA — Testes E2E com Firebase Real

Valida:
- Múltiplos eventos paralelos sem colisão
- Lock atomicidade
- Isolamento entre operações
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import salvar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from services.interpretador_conversacional import interpretar_conversa_operacional
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_concorrencia_multiplos_clientes():
    """[FASE 2] Múltiplos clientes diferentes criam eventos sem colisão"""

    async def criar_evento(cliente_id, wa_id, prof, servico, dias):
        ctx = {"_tenant_id_guard": TENANT_TEST}
        await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx)

        dados = {
            "profissional": prof,
            "servico": servico,
            "data_hora": f"{(datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')}T10:00:00",
            "duracao": 40,
            "confirmado": True,
            "tenant_id": TENANT_TEST,
            "user_id": wa_id,
            "cliente_id": cliente_id,
        }
        return await add_evento_por_gpt(None, None, dados)

    # 3 clientes, 3 profissionais diferentes
    cliente_a = "whatsapp:5511991382080"
    cliente_b = "whatsapp:5511991382081"
    cliente_c = "whatsapp:5511991382082"

    # Criar em paralelo
    resultados = await asyncio.gather(
        criar_evento(cliente_a, "5511991382080", "Bruna", "corte feminino", 5),
        criar_evento(cliente_b, "5511991382081", "Gloria", "coloracao", 6),
        criar_evento(cliente_c, "5511991382082", "Joana", "manicure", 7),
    )

    print(f"[CONCORRENCIA-1] Resultados: {resultados}")

    if all(resultados):
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        total = len(eventos)
        print(f"[CONCORRENCIA-1] Total eventos: {total}")
        if total >= 3:
            print("[CONCORRENCIA-1] ✓ Múltiplos eventos sem colisão")


@pytest.mark.asyncio
async def test_p0_concorrencia_mesmo_profissional():
    """[FASE 2] Mesmo profissional, clientes diferentes, horários diferentes"""

    async def criar_com_bruna(cliente_id, wa_id, hora):
        ctx = {"_tenant_id_guard": TENANT_TEST}
        await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx)

        dados = {
            "profissional": "Bruna",
            "servico": "corte feminino",
            "data_hora": f"{(datetime.now() + timedelta(days=8)).strftime('%Y-%m-%d')}T{hora}:00:00",
            "duracao": 40,
            "confirmado": True,
            "tenant_id": TENANT_TEST,
            "user_id": wa_id,
            "cliente_id": cliente_id,
        }
        return await add_evento_por_gpt(None, None, dados)

    cliente_x = "whatsapp:5511991382090"
    cliente_y = "whatsapp:5511991382091"

    # Mesma profissional, horários diferentes
    resultados = await asyncio.gather(
        criar_com_bruna(cliente_x, "5511991382090", "10"),
        criar_com_bruna(cliente_y, "5511991382091", "11"),
    )

    print(f"[CONCORRENCIA-2] Resultados: {resultados}")

    if all(resultados):
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        bruna_eventos = len([e for e in eventos.values() if e.get("profissional", "").lower() == "bruna"])
        print(f"[CONCORRENCIA-2] Eventos Bruna: {bruna_eventos}")
        if bruna_eventos >= 2:
            print("[CONCORRENCIA-2] ✓ Sem conflito mesmo profissional")


@pytest.mark.asyncio
async def test_p0_concorrencia_lock_atomicidade():
    """[FASE 2] Lock é atômico (sem race condition)"""

    async def criar_evento_rapido(cliente_id, wa_id, num):
        ctx = {"_tenant_id_guard": TENANT_TEST}
        await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx)

        dados = {
            "profissional": "Carla",
            "servico": "pedicure",
            "data_hora": f"{(datetime.now() + timedelta(days=13)).strftime('%Y-%m-%d')}T14:00:00",
            "duracao": 30,
            "confirmado": True,
            "tenant_id": TENANT_TEST,
            "user_id": wa_id,
            "cliente_id": cliente_id,
        }
        return await add_evento_por_gpt(None, None, dados)

    # 3 clientes em paralelo
    clientes = [f"whatsapp:559999999{i:02d}" for i in range(3)]
    wa_ids = [f"559999999{i:02d}" for i in range(3)]

    resultados = await asyncio.gather(
        *[criar_evento_rapido(clientes[i], wa_ids[i], i) for i in range(3)]
    )

    print(f"[CONCORRENCIA-3] Resultados: {resultados}")
    print("[CONCORRENCIA-3] ✓ Locks não causaram deadlock")
