"""
[P0 DIAGNÓSTICO] Verificar se tenant_id está sendo propagado corretamente
"""

import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from handlers.event_handler import add_evento_por_gpt

TENANT_TEST = "7394370553"
WA_ID = "5511991382080"
ACTOR_WA = f"whatsapp:{WA_ID}"


@pytest.mark.asyncio
async def test_p0_diagnostico_tenant_id():
    """
    Teste que passa tenant_id nos dados e verifica se é preservado
    """
    print("\n" + "="*100)
    print("[P0 DIAGNÓSTICO] Propagação de tenant_id")
    print("="*100)

    amanha = datetime.now() + timedelta(days=1)
    data_hora = f"{amanha.strftime('%Y-%m-%d')}T14:00:00"

    dados_evento = {
        "profissional": "Gloria",
        "servico": "corte feminino",
        "data_hora": data_hora,
        "duracao": 40,
        "descricao": "Corte feminino com Gloria",
        "confirmado": True,
        "tenant_id": TENANT_TEST,  # ← PASSANDO TENANT_ID
        "user_id": WA_ID,
        "cliente_id": ACTOR_WA,
    }

    print(f"\n✓ Dados de entrada:")
    print(f"  - tenant_id: {dados_evento.get('tenant_id')}")
    print(f"  - profissional: {dados_evento.get('profissional')}")
    print(f"  - servico: {dados_evento.get('servico')}")

    resultado = await add_evento_por_gpt(None, None, dados_evento)
    print(f"\n✓ add_evento_por_gpt retornou: {resultado}")
    print(f"  - Tipo: {type(resultado)}")

    assert resultado is True, f"Esperado True, recebido {resultado}"
    print("\n✅ TESTE PASSOU")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
