#!/usr/bin/env python3
"""
Bulk delete de clientes teste
Usa batch writes para deletar múltiplos documentos de uma vez
"""

import asyncio
from services.firebase_service_async import get_async_client
from datetime import datetime

# Padrões de clientes a DELETAR (são clientes de teste)
PATTERNS_DELETE = [
    "dono_tenant_lote3_",
    "user_tenant_lote3_",  # Padrão corrigido
    "usuario_",
    "bateria_p0_user_teste_",
    "cliente_",
    "diagnostico_",
    "teste",
    "t1_", "t2_", "t3_", "t17_",  # Incluiu t17
    "bruno", "carla", "diag_cliente_teste_001", "cliente_maria_001", "cliente_teste_001"
]

# Clientes a MANTER (reais)
CLIENTS_KEEP = {
    "7371670478",
    "7394370553",
    "5511991382080",
    "default"
}

async def matches_delete_pattern(client_id):
    """Verifica se cliente deve ser deletado"""
    if client_id in CLIENTS_KEEP:
        return False

    for pattern in PATTERNS_DELETE:
        if pattern in client_id:
            return True

    return False

async def bulk_delete_clientes():
    """Deleta clientes de teste em lotes"""
    client = get_async_client()

    print("\n" + "="*70)
    print("BULK DELETE - CLIENTES TESTE")
    print("="*70)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Listar todos os clientes
    print("[1] Lendo lista de clientes...\n")
    ref = client.collection("Clientes")

    clientes_para_deletar = []
    clientes_mantidos = []

    async for doc in ref.stream():
        if await matches_delete_pattern(doc.id):
            clientes_para_deletar.append(doc.id)
        else:
            clientes_mantidos.append(doc.id)

    print(f"Total de clientes: {len(clientes_para_deletar) + len(clientes_mantidos)}")
    print(f"  - A deletar: {len(clientes_para_deletar)}")
    print(f"  - A manter: {len(clientes_mantidos)}\n")

    if clientes_para_deletar:
        print(f"Clientes a manter: {sorted(clientes_mantidos)}\n")

    if not clientes_para_deletar:
        print("[OK] Nenhum cliente de teste encontrado!")
        return

    # Deletar em lotes (batch size = 100)
    print(f"[2] Deletando {len(clientes_para_deletar)} clientes em lotes...\n")

    batch_size = 100
    total_deleted = 0

    for i in range(0, len(clientes_para_deletar), batch_size):
        batch = clientes_para_deletar[i:i+batch_size]
        batch_num = (i // batch_size) + 1

        print(f"Lote {batch_num}: deletando {len(batch)} clientes...")

        # Criar batch de delete
        batch_write = client.batch()

        for cliente_id in batch:
            ref = client.document(f"Clientes/{cliente_id}")
            batch_write.delete(ref)

        # Executar batch
        try:
            await batch_write.commit()
            total_deleted += len(batch)
            print(f"  ✓ {len(batch)} deletados\n")
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:80]}\n")
            if "429" in str(e):
                print("[ALERTA] Quota esgotada! Parando limpeza.")
                break

    # Verificar quota
    print("[3] Verificando quota final...")
    try:
        ref = client.document("_test_quota/status")
        await ref.get()
        print("    ✓ Quota disponível\n")
    except Exception as e:
        if "429" in str(e):
            print("    ✗ Quota esgotada!")
        else:
            print(f"    ? Status: {str(e)[:60]}")

    print("="*70)
    print("RESUMO")
    print("="*70)
    print(f"Clientes deletados: {total_deleted}")
    print(f"Clientes mantidos: {len(clientes_mantidos)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(bulk_delete_clientes())
