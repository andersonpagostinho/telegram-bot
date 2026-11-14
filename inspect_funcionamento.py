"""Inspect working days configuration"""
import asyncio
from services.firebase_service_async import buscar_dado_em_path

async def inspecionar():
    tenant_id = "7394370553"
    config = await buscar_dado_em_path(f"Clientes/{tenant_id}")

    print("\n=== Dias de Funcionamento ===\n")
    if config:
        print("Chaves na configuração:")
        for chave in config.keys():
            if "dia" in chave.lower() or "hora" in chave.lower() or "funcionam" in chave.lower():
                print(f"  ✅ {chave}: {config[chave]}")
    else:
        print("❌ Config vazia")

asyncio.run(inspecionar())
