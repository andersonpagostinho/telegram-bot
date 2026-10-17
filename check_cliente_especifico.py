#!/usr/bin/env python3
"""Verifica um cliente específico no Firebase"""

import asyncio
from services.firebase_service_async import get_async_client

async def main():
    client = get_async_client()

    cliente_id = "5511991382080"

    print(f"\nVerificando cliente: {cliente_id}\n")

    # Verificar se o documento existe
    ref = client.document(f"Clientes/{cliente_id}")
    doc = await ref.get()

    if doc.exists:
        print(f"✓ Cliente encontrado!")
        print(f"  ID: {doc.id}")
        print(f"  Dados: {doc.to_dict()}\n")

        # Listar subcoleções
        print("Subcoleções:")
        subcols = await ref.collections()
        async for subcol in subcols:
            print(f"  - {subcol.id}")

            # Listar documentos da subcoleção
            docs = await subcol.stream()
            async for d in docs:
                print(f"      - {d.id}")
    else:
        print(f"✗ Cliente NÃO encontrado!")

    print()

if __name__ == "__main__":
    asyncio.run(main())
