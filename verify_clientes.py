#!/usr/bin/env python3
"""Verifica quais clientes ainda existem no Firebase"""

import asyncio
from services.firebase_service_async import get_async_client

CLIENTES_REAIS = {"5511991382080", "7371670478", "7394370553", "default"}
CLIENTES_TESTE = {
    "a_276b", "a_36bf", "a_7589", "a_89d7", "a_8e80", "a_a737", "a_d2c5",
    "b_0642", "b_1313", "b_57ad", "b_6b67", "b_b04d", "b_b37f"
}

async def main():
    client = get_async_client()

    print("\n" + "="*70)
    print("VERIFICACAO DE CLIENTES NO FIREBASE")
    print("="*70 + "\n")

    # Listar todos os clientes
    ref = client.collection("Clientes")

    clientes_existentes = []
    async for doc in ref.stream():
        clientes_existentes.append(doc.id)

    print(f"Total de clientes encontrados: {len(clientes_existentes)}\n")

    # Verificar clientes reais
    print("[CLIENTES REAIS - Devem existir]")
    for cliente in sorted(CLIENTES_REAIS):
        if cliente in clientes_existentes:
            print(f"  ✓ {cliente}")
        else:
            print(f"  ✗ {cliente} [DESAPARECEU!]")

    # Verificar clientes teste
    print("\n[CLIENTES TESTE - Devem estar deletados]")
    deletados = []
    ainda_existem = []

    for cliente in sorted(CLIENTES_TESTE):
        if cliente in clientes_existentes:
            ainda_existem.append(cliente)
            print(f"  ✗ {cliente} [AINDA EXISTE]")
        else:
            deletados.append(cliente)
            print(f"  ✓ {cliente} [Deletado]")

    # Resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"Clientes reais OK: {len([c for c in CLIENTES_REAIS if c in clientes_existentes])}/{len(CLIENTES_REAIS)}")
    print(f"Clientes teste deletados: {len(deletados)}/{len(CLIENTES_TESTE)}")
    print(f"Clientes teste AINDA EXISTEM: {len(ainda_existem)}")

    if ainda_existem:
        print(f"\nClientes que não foram deletados:")
        for c in ainda_existem:
            print(f"  - {c}")

    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
