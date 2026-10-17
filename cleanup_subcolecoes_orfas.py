#!/usr/bin/env python3
"""
Deleta subcoleções órfãs no Firebase
Quando um documento pai é deletado, as subcoleções ficam órfãs
"""

import asyncio
from services.firebase_service_async import get_async_client
from datetime import datetime

async def delete_subcollection_recursive(db, path):
    """Deleta recursivamente todos os documentos em uma subcoleção"""
    try:
        ref = db.collection(path)
        deleted_count = 0

        async for doc in ref.stream():
            try:
                # Deletar subcoleções do documento antes de deletar o documento
                for subcol in await doc.reference.collections():
                    await delete_subcollection_recursive(db, f"{path}/{doc.id}/{subcol.id}")

                # Deletar o documento
                await doc.reference.delete()
                deleted_count += 1
            except Exception as e:
                print(f"  [ERRO] Erro ao deletar {path}/{doc.id}: {str(e)[:60]}")

        return deleted_count
    except Exception as e:
        print(f"  [ERRO] Erro ao acessar {path}: {str(e)[:60]}")
        return 0

async def main():
    client = get_async_client()

    print("\n" + "="*70)
    print("LIMPEZA DE SUBCOLEÇÕES ÓRFÃS")
    print("="*70)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Clientes a limpar (os que foram deletados mas deixaram órfãs)
    clientes_teste = {
        "a_276b", "a_36bf", "a_7589", "a_89d7", "a_8e80", "a_a737", "a_d2c5",
        "b_0642", "b_1313", "b_57ad", "b_6b67", "b_b04d", "b_b37f"
    }

    print("[1] Deletando subcoleções órfãs dos clientes teste...\n")

    total_deleted = 0

    for i, cliente_id in enumerate(sorted(clientes_teste), 1):
        print(f"[{i}/{len(clientes_teste)}] {cliente_id}")

        # Listar e deletar todas as subcoleções deste cliente
        try:
            ref = client.document(f"Clientes/{cliente_id}")

            # Listar subcoleções
            deleted_in_client = 0

            async for subcol in ref.collections():
                # Deletar recursivamente a subcoleção
                count = await delete_subcollection_recursive(client, f"Clientes/{cliente_id}/{subcol.id}")
                deleted_in_client += count
                print(f"    ✓ {subcol.id}: {count} documentos deletados")

            total_deleted += deleted_in_client

        except Exception as e:
            print(f"    [ERRO] {str(e)[:60]}")

    # Verificar quota
    print("\n[2] Verificando quota...")
    try:
        ref = client.document("_test_quota/status")
        await ref.get()
        print("    ✓ Quota disponível")
    except Exception as e:
        if "429" in str(e):
            print("    ✗ Quota esgotada!")
        else:
            print(f"    ? Erro na verificação: {str(e)[:60]}")

    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"Total de documentos deletados: {total_deleted}")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
