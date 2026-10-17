#!/usr/bin/env python3
"""Lista todos os clientes para diagnóstico"""

import asyncio
from services.firebase_service_async import get_async_client

async def main():
    client = get_async_client()

    print("\nListando TODOS os clientes...\n")

    ref = client.collection("Clientes")

    clientes = []
    async for doc in ref.stream():
        clientes.append(doc.id)

    clientes_sorted = sorted(clientes)

    print(f"Total: {len(clientes_sorted)}\n")

    # Mostrar primeiros 50
    print("Primeiros 50 clientes:")
    for i, c in enumerate(clientes_sorted[:50], 1):
        print(f"  {i:3d}. {c}")

    if len(clientes_sorted) > 50:
        print(f"\n... e mais {len(clientes_sorted) - 50} clientes")

    # Verificar padrões
    print("\n" + "="*70)
    print("ANÁLISE DE PADRÕES")
    print("="*70)

    # Contar por prefixo
    prefixos = {}
    for c in clientes:
        prefix = c[:2]
        prefixos[prefix] = prefixos.get(prefix, 0) + 1

    print("\nClientes por prefixo:")
    for p in sorted(prefixos.keys()):
        count = prefixos[p]
        print(f"  {p}*: {count}")

if __name__ == "__main__":
    asyncio.run(main())
