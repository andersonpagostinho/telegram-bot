#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("FIREBASE_CREDENTIALS_B64", os.getenv("FIREBASE_CREDENTIALS_B64", ""))

async def listar_servicos():
    from services.firebase_service_async import get_firestore_async

    db = get_firestore_async()
    tenant = "7394370553"

    try:
        docs = db.collection(f"Clientes/{tenant}/ServicosNegocio").stream()
        print("Servicos cadastrados em ServicosNegocio:")
        async for doc in docs:
            data = doc.to_dict()
            print(f"  - {doc.id}:")
            print(f"      nome: {data.get('nome')}")
            print(f"      id: {data.get('id')}")
            print(f"      preco: {data.get('preco')}")
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(listar_servicos())
