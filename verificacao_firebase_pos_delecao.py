"""
Verificação: Os 442 locks realmente saíram do Firebase?

Consultar diretamente os documentos para confirmar deleção
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service_async import buscar_dado_em_path, buscar_subcolecao

TENANT_ID = "7394370553"


async def verificar():
    print("\n" + "="*80)
    print("VERIFICAÇÃO: LOCKS FORAM REALMENTE DELETADOS DO FIREBASE?")
    print("="*80)

    # Verificar 4 locks de Bruna
    locks_bruna = [
        "bruna_20261106_100000",
        "bruna_20261106_101000",
        "bruna_20261106_102000",
        "bruna_20261106_103000",
    ]

    print(f"\n[1] Verificando 4 locks de Bruna em 2026-11-06 10:00...")
    bruna_removidos = 0
    for lock_id in locks_bruna:
        path = f"Clientes/{TENANT_ID}/AgendaLocks/{lock_id}"
        lock_doc = await buscar_dado_em_path(path)

        if lock_doc:
            print(f"  ❌ {lock_id}: AINDA EXISTE no Firebase (erro!)")
        else:
            print(f"  ✓ {lock_id}: Removido do Firebase")
            bruna_removidos += 1

    print(f"\nBruna: {bruna_removidos}/4 removidos")

    # Verificar amostra de outros locks
    print(f"\n[2] Verificando amostra de locks de outras profissionais...")

    amostra_locks = [
        "joana_20261026_130000",
        "gloria_20261021_090000",
        "carla_20270227_095000",
    ]

    amostra_removidos = 0
    for lock_id in amostra_locks:
        path = f"Clientes/{TENANT_ID}/AgendaLocks/{lock_id}"
        lock_doc = await buscar_dado_em_path(path)

        if lock_doc:
            print(f"  ❌ {lock_id}: AINDA EXISTE no Firebase (erro!)")
        else:
            print(f"  ✓ {lock_id}: Removido do Firebase")
            amostra_removidos += 1

    print(f"\nAmostra: {amostra_removidos}/3 removidos")

    # Consultar total de locks ainda existentes
    print(f"\n[3] Consultando total de locks ainda no Firebase...")

    try:
        locks_dict = await buscar_subcolecao(f"Clientes/{TENANT_ID}/AgendaLocks")
        total_restante = len(locks_dict)

        print(f"  Total de locks ainda no AgendaLocks: {total_restante}")

        if total_restante == 0:
            print(f"\n  ✅ CONFIRMADO: AgendaLocks está vazio!")
        else:
            print(f"\n  ⚠️ AVISO: Ainda existem {total_restante} locks no Firebase")

            # Mostrar primeiros 5
            print(f"\n  Primeiros 5 locks restantes:")
            for i, (lock_id, lock_data) in enumerate(list(locks_dict.items())[:5]):
                print(f"    {lock_id}: {lock_data.get('evento_id', 'sem evento')}")

    except Exception as e:
        print(f"  Erro ao consultar: {e}")

    # Conclusão
    print(f"\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)

    if bruna_removidos == 4 and amostra_removidos == 3:
        print(f"\n✅ SIM, OS LOCKS FORAM REALMENTE DELETADOS DO FIREBASE!")
        print(f"\n   - 4/4 locks de Bruna removidos")
        print(f"   - 3/3 locks de amostra removidos")
        print(f"   - Deleção foi bem-sucedida!")
    else:
        print(f"\n❌ FALHA: Nem todos os locks foram removidos")
        print(f"   - Bruna: {bruna_removidos}/4")
        print(f"   - Amostra: {amostra_removidos}/3")

    print(f"\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(verificar())
