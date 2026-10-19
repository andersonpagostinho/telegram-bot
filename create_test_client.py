#!/usr/bin/env python3
"""Cria cliente permanente de teste E2E"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Carregar env antes de importar Firebase
os.environ.setdefault("FIREBASE_CREDENTIALS_B64", os.getenv("FIREBASE_CREDENTIALS_B64", ""))

from services.firebase_service_async import salvar_dado_em_path

async def criar_cliente_teste():
    """Cria cliente permanente de teste whats233343848"""

    TENANT_ID = "7394370553"
    CLIENTE_ID = "whats233343848"

    print("\n" + "="*80)
    print("CRIANDO CLIENTE DE TESTE PERMANENTE")
    print("="*80)
    print(f"\nTenant: {TENANT_ID}")
    print(f"Cliente: {CLIENTE_ID}")

    # Criar documento do cliente
    cliente_doc = {
        "id": CLIENTE_ID,
        "nome": "Cliente Teste E2E",
        "telefone": "5533843343848",
        "email": "teste@example.com",
        "tipo": "cliente",
        "ativo": True,
        "criado_em": "2026-10-19T19:00:00Z",
        "notas": "Cliente permanente para testes E2E do webhook Flask"
    }

    try:
        await salvar_dado_em_path(
            f"Clientes/{TENANT_ID}/Clientes/{CLIENTE_ID}",
            cliente_doc
        )
        print(f"[OK] Cliente criado")
    except Exception as e:
        print(f"[ERR] Erro ao criar cliente: {e}")

    # Criar sessao
    sessao_doc = {
        "actor_id": f"whatsapp:{CLIENTE_ID}",
        "tenant_id": TENANT_ID,
        "tipo_usuario": "cliente",
        "estado_fluxo": "ativo",
        "historico_texto": [],
        "criado_em": "2026-10-19T19:00:00Z"
    }

    try:
        await salvar_dado_em_path(
            f"Clientes/{TENANT_ID}/Sessoes/whatsapp:{CLIENTE_ID}",
            sessao_doc
        )
        print(f"[OK] Sessao criada")
    except Exception as e:
        print(f"[ERR] Erro ao criar sessao: {e}")

    # Criar ator
    ator_doc = {
        "actor_id": f"whatsapp:{CLIENTE_ID}",
        "tipo_usuario": "cliente",
        "user_id": CLIENTE_ID,
        "canal": "whatsapp",
        "tenant_id": TENANT_ID,
        "criado_em": "2026-10-19T19:00:00Z"
    }

    try:
        await salvar_dado_em_path(
            f"Clientes/{TENANT_ID}/Atores/whatsapp:{CLIENTE_ID}",
            ator_doc
        )
        print(f"[OK] Ator criado")
    except Exception as e:
        print(f"[ERR] Erro ao criar ator: {e}")

    print("\n" + "="*80)
    print("CLIENTE DE TESTE PERMANENTE CRIADO COM SUCESSO")
    print("="*80)
    print(f"\nUse este cliente para todos os testes E2E:")
    print(f"  CLIENTE_ID: {CLIENTE_ID}")
    print(f"  actor_id: whatsapp:{CLIENTE_ID}")
    print(f"  Telefone: 5533843343848")

if __name__ == "__main__":
    asyncio.run(criar_cliente_teste())
