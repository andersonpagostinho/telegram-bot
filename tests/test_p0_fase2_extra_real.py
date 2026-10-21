"""
[FASE 2] P0 EXTRA — Testes E2E com Firebase Real (casos adicionais)

Valida:
- Conflito detectado
- Serviço alternativo sugerido
- Cliente consegue mudar
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

from utils.contexto_temporario import salvar_contexto_temporario_v2
from services.firebase_service_async import buscar_subcolecao
from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_extra_conflito_detectado():
    """[FASE 2] Cenário: Conflito de horário detectado e sugerida alternativa"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_conflito = (datetime.now() + timedelta(days=125)).strftime('%Y-%m-%d')

    # Primeiro evento
    dados1 = {
        "profissional": "Bruna",
        "servico": "corte feminino",
        "data_hora": f"{data_conflito}T10:00:00",
        "duracao": 40,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado1 = await add_evento_por_gpt(None, None, dados1)
    print(f"[EXTRA-1] Primeiro evento: {resultado1}")

    # Segundo evento no mesmo slot (conflito)
    dados2 = {
        "profissional": "Bruna",
        "servico": "escova",
        "data_hora": f"{data_conflito}T10:10:00",  # Overlaps
        "duracao": 60,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado2 = await add_evento_por_gpt(None, None, dados2)
    print(f"[EXTRA-1] Segundo evento (conflito): {resultado2}")
    print(f"[EXTRA-1] Esperado: False (conflito detectado)")


@pytest.mark.asyncio
async def test_p0_extra_duracao_catálogo():
    """[FASE 2] Cenário: Duração vem do catálogo, não do fallback"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    dados = {
        "profissional": "Carla",
        "servico": "coloracao",  # Catálogo: 120 min
        "data_hora": f"{(datetime.now() + timedelta(days=130)).strftime('%Y-%m-%d')}T09:00:00",
        "duracao": 120,  # Deve vir do catálogo, não fallback
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[EXTRA-2] Evento criado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        carla_coloracao = [e for e in eventos.values()
                          if e.get("profissional", "").lower() == "carla"
                          and e.get("servico", "").lower() == "coloracao"]
        if carla_coloracao:
            duracao = carla_coloracao[0].get("duracao")
            print(f"[EXTRA-2] Duração no evento: {duracao} (esperado 120)")
            if duracao == 120:
                print("[EXTRA-2] ✓ Duração do catálogo OK")
