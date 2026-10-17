#!/usr/bin/env python3
"""
Limpeza segura de Clientes teste no Firebase
Monitora consumo a cada deleção para evitar esgotamento de quota

Clientes a manter (REAIS):
  - 5511991382080
  - 7371670478
  - 7394370553

Clientes a deletar (TESTE):
  - a_276b, a_36bf, a_7589, a_89d7, a_8e80, a_a737, a_d2c5
  - b_0642, b_1313, b_57ad, b_6b67, b_b04d, b_b37f
"""

import asyncio
import json
from pathlib import Path
from services.firebase_service_async import get_async_client
from datetime import datetime

# Clientes a manter
CLIENTES_REAIS = {
    "5511991382080",
    "7371670478",
    "7394370553",
    "default"  # Manter também
}

# Clientes a deletar (dados de teste)
CLIENTES_TESTE = {
    "a_276b", "a_36bf", "a_7589", "a_89d7", "a_8e80", "a_a737", "a_d2c5",
    "b_0642", "b_1313", "b_57ad", "b_6b67", "b_b04d", "b_b37f"
}

async def check_quota():
    """Verifica se quota ainda está disponível"""
    client = get_async_client()
    try:
        ref = client.document("_test_quota/status")
        await ref.get()
        return True
    except Exception as e:
        if "429" in str(e):
            return False
        return True

async def count_operations_in_client(client, tenant_id):
    """Conta quantas operações serão necessárias para deletar um cliente"""
    count = 0
    try:
        ref = client.collection(f"Clientes/{tenant_id}/Emails")
        docs = await ref.stream()
        async for _ in docs:
            count += 1

        ref = client.collection(f"Clientes/{tenant_id}/Eventos")
        docs = await ref.stream()
        async for _ in docs:
            count += 1

        ref = client.collection(f"Clientes/{tenant_id}/Relatorios")
        docs = await ref.stream()
        async for _ in docs:
            count += 1

        ref = client.collection(f"Clientes/{tenant_id}/Tarefas")
        docs = await ref.stream()
        async for _ in docs:
            count += 1

        # + 1 para o próprio documento do cliente
        return count + 1
    except:
        return 1

async def delete_client_recursive(client, tenant_id):
    """Deleta recursivamente todas as subcoleções de um cliente"""
    deleted_count = 0

    # Listar e deletar documentos de cada subcoleção
    subcoleções = ["Emails", "Eventos", "Relatorios", "Tarefas", "UserPrioritySettings", "Usuarios"]

    for subcol in subcoleções:
        try:
            ref = client.collection(f"Clientes/{tenant_id}/{subcol}")
            docs = await ref.stream()

            async for doc in docs:
                try:
                    await doc.reference.delete()
                    deleted_count += 1
                except Exception as e:
                    print(f"    [ERRO ao deletar {subcol}/{doc.id}] {str(e)[:60]}")
        except:
            pass  # Subcoleção pode não existir

    # Deletar o próprio documento do cliente
    try:
        ref = client.document(f"Clientes/{tenant_id}")
        await ref.delete()
        deleted_count += 1
    except Exception as e:
        print(f"    [ERRO ao deletar cliente] {str(e)[:60]}")

    return deleted_count

async def main():
    print("\n" + "="*70)
    print("LIMPEZA FIREBASE - CLIENTES TESTE")
    print("="*70)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    client = get_async_client()

    # Verificar quota inicial
    print("[1] Verificando quota inicial...")
    quota_ok = await check_quota()
    if not quota_ok:
        print("    [ERRO] Quota esgotada! Abortando limpeza.")
        return
    print("    [OK] Quota disponível\n")

    # Listar clientes a deletar
    print("[2] Clientes a deletar:")
    total_ops = 0
    client_ops = {}

    for tenant_id in sorted(CLIENTES_TESTE):
        ops = await count_operations_in_client(client, tenant_id)
        client_ops[tenant_id] = ops
        total_ops += ops
        print(f"    - {tenant_id}: ~{ops} ops")

    print(f"\n    Total estimado: ~{total_ops} operações")
    print(f"    (quota disponível: 100k reads + 100k writes = 200k total)\n")

    print("[3] Deletando clientes teste...")
    total_deleted = 0
    quota_checks = 0

    for i, tenant_id in enumerate(sorted(CLIENTES_TESTE), 1):
        print(f"\n  [{i}/{len(CLIENTES_TESTE)}] Deletando {tenant_id}...")

        deleted = await delete_client_recursive(client, tenant_id)
        total_deleted += deleted
        quota_checks += 1

        print(f"      ✓ Deletados {deleted} documentos")

        # Verificar quota a cada 3 clientes
        if quota_checks % 3 == 0:
            quota_ok = await check_quota()
            if not quota_ok:
                print(f"\n    [ALERTA] Quota esgotada após {i} clientes!")
                print(f"    [RESUMO] Total deletado até agora: {total_deleted} documentos")
                return
            print(f"      [CHECK] Quota OK (verificação #{quota_checks//3})")

    # Verificação final
    print("\n[4] Verificação final de quota...")
    quota_ok = await check_quota()
    if quota_ok:
        print("    [OK] Quota ainda disponível após limpeza")
    else:
        print("    [AVISO] Quota pode estar próximo do limite")

    # Resumo
    print("\n" + "="*70)
    print("RESUMO DA LIMPEZA")
    print("="*70)
    print(f"Clientes deletados: {len(CLIENTES_TESTE)}")
    print(f"Total de documentos removidos: {total_deleted}")
    print(f"Clientes mantidos: {len(CLIENTES_REAIS)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
