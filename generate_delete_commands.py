#!/usr/bin/env python3
"""
Gera arquivo com comandos firebase firestore:delete para todos os clientes de teste
Preserva: 5511991382080, 7371670478, 7394370553, whatsapp:5511991382080
"""

import asyncio
from services.firebase_service_async import get_async_client

KEEP = {
    "5511991382080",
    "7371670478",
    "7394370553",
    "default",
    "whatsapp:5511991382080"  # Cliente real do WhatsApp
}

async def main():
    client = get_async_client()

    print("\n[1] Lendo TODOS os clientes do Firebase...\n")

    ref = client.collection("Clientes")

    clientes_delete = []
    clientes_keep = []

    async for doc in ref.stream():
        if doc.id in KEEP:
            clientes_keep.append(doc.id)
        else:
            clientes_delete.append(doc.id)

    print(f"Total encontrado: {len(clientes_delete) + len(clientes_keep)}")
    print(f"  - A deletar: {len(clientes_delete)}")
    print(f"  - A manter: {len(clientes_keep)}\n")

    print("Clientes a manter:")
    for c in sorted(clientes_keep):
        print(f"  ✓ {c}")
    print()

    # Gerar arquivo de comandos
    print("[2] Gerando arquivo de comandos...\n")

    output_file = "delete_commands.ps1"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Script PowerShell para deletar todos os clientes de teste\n")
        f.write("# Gerado automaticamente\n")
        f.write("# ATENCAO: Revise antes de rodar!\n\n")
        f.write('$PROJECT = "projeto-agente-inteligente"\n')
        f.write('$deleted = 0\n')
        f.write('$failed = 0\n\n')

        for cliente in sorted(clientes_delete):
            # Escapar aspas se houver
            cliente_escaped = cliente.replace('"', '\"')
            f.write(f'Write-Host -NoNewline "  Deletando {cliente}... "\n')
            f.write(f'$result = & firebase firestore:delete --project=$PROJECT "Clientes/{cliente_escaped}" --recursive --yes 2>$null\n')
            f.write(f'if ($LASTEXITCODE -eq 0) {{\n')
            f.write(f'    Write-Host "✓"\n')
            f.write(f'    $deleted++\n')
            f.write(f'}} else {{\n')
            f.write(f'    Write-Host "✗"\n')
            f.write(f'    $failed++\n')
            f.write(f'}}\n\n')

        f.write('Write-Host ""\n')
        f.write('Write-Host "Deletados: $deleted"\n')
        f.write('Write-Host "Falhados: $failed"\n')

    print(f"✓ Arquivo gerado: {output_file}\n")
    print(f"Contém {len(clientes_delete)} comandos de delete\n")

    print("Para rodar:")
    print(f"  powershell .\\{output_file}\n")

if __name__ == "__main__":
    asyncio.run(main())
