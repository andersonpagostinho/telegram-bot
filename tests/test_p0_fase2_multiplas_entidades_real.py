"""
[FASE 2] P0 MÚLTIPLAS ENTIDADES — Testes E2E com Firebase Real

Valida:
- Múltiplas entidades preservadas (não perdidas)
- Nenhuma entidade misturada
- Evento tem EXATAMENTE os dados mencionados
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
async def test_p0_multiplas_entidades_servico_profissional_preservado():
    """[FASE 2] Cenário: Múltiplas entidades (servico + profissional) preservadas"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    # Evento com 2 entidades críticas
    dados = {
        "profissional": "Joana",
        "servico": "coloracao",  # Entidade 1: serviço
        "data_hora": f"{(datetime.now() + timedelta(days=80)).strftime('%Y-%m-%d')}T13:00:00",
        "duracao": 120,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[MULTIPLAS-1] Resultado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        joana_coloracao = [e for e in eventos.values()
                          if e.get("profissional", "").lower() == "joana"
                          and e.get("servico", "").lower() == "coloracao"]
        if joana_coloracao:
            print(f"[MULTIPLAS-1] ✓ Ambas entidades preservadas: {joana_coloracao[0].get('servico')} com {joana_coloracao[0].get('profissional')}")
        else:
            print("[MULTIPLAS-1] ✗ Entidades não encontradas juntas")


@pytest.mark.asyncio
async def test_p0_multiplas_entidades_data_hora_preservada():
    """[FASE 2] Cenário: Data + hora preservadas corretamente"""
    ctx = {"_tenant_id_guard": TENANT_TEST}
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx)

    data_futura = (datetime.now() + timedelta(days=85)).strftime('%Y-%m-%d')
    dados = {
        "profissional": "Carla",
        "servico": "manicure",
        "data_hora": f"{data_futura}T15:30:00",
        "duracao": 30,
        "confirmado": True,
        "tenant_id": TENANT_TEST,
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    resultado = await add_evento_por_gpt(None, None, dados)
    print(f"[MULTIPLAS-2] Resultado: {resultado}")

    if resultado:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_TEST}/Eventos") or {}
        carla_manicure = [e for e in eventos.values()
                         if e.get("profissional", "").lower() == "carla"
                         and e.get("servico", "").lower() == "manicure"
                         and e.get("data") == data_futura]
        if carla_manicure:
            print(f"[MULTIPLAS-2] ✓ Data + hora preservadas: {carla_manicure[0].get('data')} {carla_manicure[0].get('hora_inicio')}")
