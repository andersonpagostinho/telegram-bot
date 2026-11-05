"""
P0.27.8 — Execução Real: Deletar 442 locks órfãos

Autorização recebida! Executar dry_run=False
"""

import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.agenda_lock_service import liberar_locks_orfaos_expirados
from services.firebase_service_async import buscar_dado_em_path

TENANT_ID = "7394370553"


async def executar_delecao():
    """Executar deleção real dos 442 locks"""
    print("\n" + "#"*80)
    print("# P0.27.8 — EXECUÇÃO REAL: DELEÇÃO DE 442 LOCKS ÓRFÃOS")
    print("#"*80)

    print(f"\n⚠️ ATENÇÃO: Executando deleção real em tenant {TENANT_ID}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print(f"   Esperado: deletados=442")

    print(f"\n[EXECUTANDO] liberar_locks_orfaos_expirados(dono_id='{TENANT_ID}', dry_run=False)...")

    try:
        resultado = await liberar_locks_orfaos_expirados(
            dono_id=TENANT_ID,
            dry_run=False  # ← EXECUÇÃO REAL
        )

        print(f"\n" + "="*80)
        print("RESULTADO DA EXECUÇÃO")
        print("="*80)

        print(f"\n✓ Resultado:")
        print(f"  Identificados: {resultado['identificados']}")
        print(f"  Deletados: {resultado['deletados']}")
        print(f"  Modo: {resultado['modo']}")

        if resultado['deletados'] == 442:
            print(f"\n✅ SUCESSO: 442 locks foram deletados!")
        else:
            print(f"\n⚠️ AVISO: Esperado 442, deletado {resultado['deletados']}")

        # Validação pós-deleção
        print(f"\n" + "="*80)
        print("VALIDAÇÃO PÓS-DELEÇÃO")
        print("="*80)

        print(f"\nValidando que os 4 locks de Bruna foram removidos...")

        locks_bruna = [
            "bruna_20261106_100000",
            "bruna_20261106_101000",
            "bruna_20261106_102000",
            "bruna_20261106_103000",
        ]

        removidos = []
        nao_removidos = []

        for lock_id in locks_bruna:
            path = f"Clientes/{TENANT_ID}/AgendaLocks/{lock_id}"
            lock_doc = await buscar_dado_em_path(path)

            if lock_doc:
                nao_removidos.append(lock_id)
                print(f"  ❌ {lock_id}: AINDA EXISTE (erro!)")
            else:
                removidos.append(lock_id)
                print(f"  ✓ {lock_id}: Removido")

        print(f"\nResumo pós-deleção:")
        print(f"  Removidos: {len(removidos)}/4")
        print(f"  Ainda existem: {len(nao_removidos)}/4")

        if len(removidos) == 4:
            print(f"\n✅ CONFIRMADO: Os 4 locks de Bruna foram removidos com sucesso!")
            print(f"\n   Próximo passo: Testar novo agendamento para Bruna 10:00 em 2026-11-06")
        else:
            print(f"\n🔴 ERRO: Nem todos os locks foram removidos!")

        print(f"\n" + "#"*80)
        print(f"# P0.27.8 — EXECUÇÃO CONCLUÍDA")
        print(f"#"*80 + "\n")

        return len(removidos) == 4

    except Exception as e:
        print(f"❌ Erro durante deleção: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    sucesso = await executar_delecao()
    if sucesso:
        print("✅ Limpeza de locks concluída com sucesso!")
        print("   Status: PRONTO PARA TESTE DE NOVO AGENDAMENTO")
    else:
        print("❌ Limpeza falhou ou incompleta")


if __name__ == "__main__":
    asyncio.run(main())
