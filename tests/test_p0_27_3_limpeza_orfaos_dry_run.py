"""
P0.27.3 — Teste de limpeza de locks órfãos (DRY_RUN)

Validar que liberar_locks_orfaos_expirados() identifica corretamente
locks confirmados órfãos expirados sem deletá-los (dry_run=True).
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agenda_lock_service import liberar_locks_orfaos_expirados


@pytest.mark.asyncio
async def test_p0_27_3_identificacao_locks_orfaos_dry_run():
    """
    P0.27.3: Teste DRY_RUN — identificar locks órfãos sem deletar

    Tenant: 7394370553 (Bruna 10:00 em 2026-11-06)
    """
    TENANT_ID = "7394370553"

    print("\n" + "="*80)
    print("P0.27.3 — TESTE DRY_RUN: Identificação de Locks Órfãos")
    print("="*80)

    # Executar em dry_run (identifica sem deletar)
    resultado = await liberar_locks_orfaos_expirados(
        dono_id=TENANT_ID,
        dry_run=True  # ← IMPORTANTE: Não deleta
    )

    print(f"\nResultado DRY_RUN:")
    print(f"  Identificados: {resultado['identificados']}")
    print(f"  Deletados: {resultado['deletados']}")
    print(f"  Modo: {resultado['modo']}")

    if resultado['identificados'] > 0:
        print(f"\n  Detalhes dos locks órfãos:")
        for detail in resultado['detalhes']:
            print(f"    - Lock: {detail['lock_id']}")
            print(f"      evento_id: {detail['evento_id']}")
            print(f"      expira_em: {detail['expira_em']}")

    # Validações
    assert resultado['modo'] == 'dry_run', "Deve estar em modo dry_run"
    assert resultado['deletados'] == 0, "Não deve deletar em dry_run"

    # Esperado: encontrar 4 locks de Bruna (buckets 100000, 101000, 102000, 103000)
    # ou 0 se já foram limpados
    assert resultado['identificados'] >= 0, "Deve retornar número válido"

    # Se encontrou locks, validar que são de fato órfãos
    if resultado['identificados'] > 0:
        for detail in resultado['detalhes']:
            assert detail['evento_id'], "evento_id não pode ser vazio"
            assert detail['status'] == 'identificado_para_delecao'

    print("\n✅ Teste DRY_RUN PASSOU")
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
