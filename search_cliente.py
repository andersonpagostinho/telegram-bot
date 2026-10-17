#!/usr/bin/env python3
"""Busca um cliente em toda a coleção"""

import asyncio
from services.firebase_service_async import get_async_client

async def main():
    client = get_async_client()

    target = "5511991382080"

    print(f"\nBuscando cliente: {target}\n")
    print("Lendo todos os clientes da coleção...\n")

    ref = client.collection("Clientes")

    found = False
    count = 0

    async for doc in ref.stream():
        count += 1
        if doc.id == target:
            found = True
            print(f"✓ ENCONTRADO NA POSIÇÃO {count}!")
            print(f"  ID: {doc.id}")
            print(f"  Dados: {doc.to_dict()}\n")
            break

    if not found:
        print(f"✗ NÃO ENCONTRADO após varrer {count} documentos\n")

    print(f"Total de clientes verificados: {count}")

if __name__ == "__main__":
    asyncio.run(main())
