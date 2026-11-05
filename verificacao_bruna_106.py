"""
P0.27.5 — Verificação específica dos 4 locks de Bruna em 2026-11-06

Por que não estão entre os 434 identificados?
1. Ainda existem no Firestore?
2. Se existem, por que não foram identificados?
3. Status, expiração, evento?
"""

import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service_async import buscar_dado_em_path

TENANT_ID = "7394370553"

LOCKS_BRUNA_106 = [
    "bruna_20261106_100000",
    "bruna_20261106_101000",
    "bruna_20261106_102000",
    "bruna_20261106_103000",
]


async def verificar_locks():
    """Verificar cada um dos 4 locks de Bruna em 2026-11-06"""
    print("\n" + "="*80)
    print("P0.27.5 — VERIFICAÇÃO ESPECÍFICA: BRUNA 10:00 EM 2026-11-06")
    print("="*80)

    resultado = {
        "existem": [],
        "nao_existem": [],
        "nao_expirados": [],
        "analise": []
    }

    for lock_id in LOCKS_BRUNA_106:
        print(f"\n[{lock_id}]")
        path = f"Clientes/{TENANT_ID}/AgendaLocks/{lock_id}"

        try:
            lock_data = await buscar_dado_em_path(path)

            if lock_data:
                resultado["existem"].append(lock_id)
                print(f"  ✓ EXISTE no Firestore")

                status = lock_data.get("status")
                evento_id = lock_data.get("evento_id")
                expira_em_str = lock_data.get("expira_em")
                timestamp_lock = lock_data.get("timestamp_lock")

                print(f"    status: {status}")
                print(f"    evento_id: {evento_id}")
                print(f"    expira_em: {expira_em_str}")
                print(f"    timestamp_lock: {timestamp_lock}")

                # Verificar expiração
                if expira_em_str:
                    try:
                        expira_em = datetime.fromisoformat(expira_em_str)
                        agora = datetime.now()
                        expirado = expira_em <= agora

                        print(f"    Expirado? {expirado}")
                        print(f"      expira_em: {expira_em}")
                        print(f"      agora: {agora}")

                        if not expirado:
                            resultado["nao_expirados"].append(lock_id)
                            print(f"      ⚠️ NÃO EXPIRADO - Não seria removido!")
                    except Exception as e:
                        print(f"    ❌ Erro ao verificar expiração: {e}")

                # Análise
                analise = {
                    "lock_id": lock_id,
                    "existe": True,
                    "status": status,
                    "evento_id": evento_id,
                    "expirado": expirado if expira_em_str else None
                }
                resultado["analise"].append(analise)

            else:
                resultado["nao_existem"].append(lock_id)
                print(f"  ❌ NÃO EXISTE (foi deletado ou nunca foi criado)")

        except Exception as e:
            print(f"  ❌ Erro ao buscar: {e}")
            resultado["nao_existem"].append(lock_id)

    # Resumo
    print(f"\n" + "="*80)
    print("RESUMO — BRUNA 2026-11-06 10:00")
    print("="*80)

    print(f"\n✓ Existem no Firestore: {len(resultado['existem'])}/4")
    for lock_id in resultado["existem"]:
        print(f"    {lock_id}")

    print(f"\n❌ Não existem: {len(resultado['nao_existem'])}/4")
    for lock_id in resultado["nao_existem"]:
        print(f"    {lock_id}")

    print(f"\n⚠️ Existem mas NÃO EXPIRADOS: {len(resultado['nao_expirados'])}/4")
    for lock_id in resultado["nao_expirados"]:
        print(f"    {lock_id} — Será preservado (ainda válido)")

    # Conclusão
    print(f"\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)

    if len(resultado["existem"]) == 0:
        print("\n✓ Os 4 locks de Bruna JÁ FORAM DELETADOS")
        print("  Status: Problema resolvido")
        print("  Novo agendamento em 2026-11-06 10:00 funcionará ✅")
    elif len(resultado["nao_expirados"]) == 4:
        print("\n⚠️ Os 4 locks ainda existem e NÃO estão expirados")
        print("  Status: Ainda não deletáveis")
        print("  Ação: Aguardar expiração em 24h")
    elif len(resultado["nao_expirados"]) == 0:
        print("\n🔴 Os 4 locks existem, estão expirados, mas NÃO foram identificados")
        print("  Status: BUG — deveriam estar entre os 434!")
        print("  Motivo possível: evento_id diferente, status não 'confirmado', etc")

    print(f"\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(verificar_locks())
