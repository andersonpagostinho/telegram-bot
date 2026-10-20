"""
[P0626] Debug — Validar se Profissionais estão sendo carregados
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

import asyncio
from services.firebase_service_async import buscar_subcolecao

async def test_load_profissionais():
    """Verificar se os profissionais estão disponíveis em Firestore"""

    TENANT = "7394370553"

    print(f"\n[DEBUG] Carregando profissionais para tenant {TENANT}...")

    profs = await buscar_subcolecao(f"Clientes/{TENANT}/Profissionais")

    print(f"\nResultado: {profs}")
    print(f"Tipo: {type(profs)}")
    print(f"Vazio? {not bool(profs)}")

    if profs:
        print(f"\nProfissionais encontrados: {len(profs)}")
        for nome, dados in profs.items():
            servicos = dados.get("servicos", [])
            print(f"  - {nome}: {servicos}")
    else:
        print("\n❌ Nenhum profissional carregado!")
        print("   Isso explicaria por que 'corte feminino' não é encontrado")
        print("   (lista de serviços fica vazia)")

if __name__ == "__main__":
    asyncio.run(test_load_profissionais())
