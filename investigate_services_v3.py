#!/usr/bin/env python3
"""Investiga estrutura de ServicosNegocio"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("FIREBASE_CREDENTIALS_B64", os.getenv("FIREBASE_CREDENTIALS_B64", ""))

async def investigar():
    from services.firebase_service_async import get_async_client

    db = get_async_client()
    tenant = "7394370553"

    print("\n" + "="*80)
    print("INVESTIGACAO DE ServicosNegocio")
    print("="*80)

    # 1. Listar ServicosNegocio
    print(f"\n[1] Listando colecao Clientes/{tenant}/ServicosNegocio:")
    try:
        docs = db.collection(f"Clientes/{tenant}/ServicosNegocio").stream()
        servicos_encontrados = []
        async for doc in docs:
            data = doc.to_dict()
            servicos_encontrados.append(doc.id)
            print(f"  ID: '{doc.id}'")
            print(f"  Dados: {data}")
            print()

        if not servicos_encontrados:
            print("  [VAZIO] Colecao nao tem documentos!")
        else:
            print(f"  Total: {len(servicos_encontrados)} documentos")
            print(f"  IDs encontrados: {servicos_encontrados}")
    except Exception as e:
        print(f"  [ERRO] {e}")
        import traceback
        traceback.print_exc()

    # 2. Verificar estrutura em Profissionais
    print(f"\n[2] Servicos listados em Profissionais:")
    try:
        docs = db.collection(f"Clientes/{tenant}/Profissionais").stream()
        async for doc in docs:
            data = doc.to_dict()
            servicos = data.get('servicos', [])
            nome_prof = data.get('nome', doc.id)
            print(f"  {nome_prof}: {servicos}")
    except Exception as e:
        print(f"  [ERRO] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(investigar())
