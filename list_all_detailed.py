#!/usr/bin/env python3
"""Lista TODOS os clientes com detalhes"""

import asyncio
from services.firebase_service_async import get_async_client

async def main():
    client = get_async_client()

    ref = client.collection("Clientes")

    clientes = []
    async for doc in ref.stream():
        clientes.append(doc.id)

    clientes_sorted = sorted(clientes)

    print(f"\nTotal de clientes: {len(clientes_sorted)}\n")

    # Procurar pelo cliente específico
    target = "5511991382080"
    if target in clientes_sorted:
        idx = clientes_sorted.index(target)
        print(f"✓ ENCONTRADO! Na posição {idx + 1}")
    else:
        print(f"✗ NÃO ENCONTRADO na lista")

    # Mostrar todos os clientes
    print("\nLista completa de clientes:")
    for i, c in enumerate(clientes_sorted, 1):
        print(f"{i:4d}. {c}")

if __name__ == "__main__":
    asyncio.run(main())
