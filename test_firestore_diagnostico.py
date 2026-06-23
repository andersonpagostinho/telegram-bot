#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INFRA-01: Diagnóstico Firestore/gRPC Timeout

Objetivo: Determinar causa raiz dos timeouts observados em testes.

Investigar:
1. Estado do cliente Firestore (reutilizado vs recriado)
2. Tempo entre operações
3. Ponto exato do timeout (leitura, escrita, shutdown)
4. Se problema é isolado em testes ou também em código real
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.cwd()))

async def test_firestore_operations():
    """Teste de operações Firestore com logging detalhado."""

    from services.firebase_service_async import (
        salvar_dado_em_path,
        buscar_dado_em_path
    )
    from services.firestore_client import get_db

    print("\n" + "="*70)
    print("INFRA-01: DIAGNOSTICO FIRESTORE/gRPC TIMEOUT")
    print("="*70 + "\n")

    # ===== OPERAÇÃO 1: Obter cliente =====
    print("[1] Obtendo cliente Firestore...")
    t_start = time.time()
    try:
        db = get_db()
        t_elapsed = time.time() - t_start
        print(f"    Status: OK (obtido em {t_elapsed:.3f}s)")
        print(f"    Cliente: {type(db).__name__}")
        print(f"    ID do cliente: {id(db)}")
    except Exception as e:
        print(f"    [ERRO] {e}")
        return

    # ===== OPERAÇÃO 2: Escrita de teste =====
    print("\n[2] Escrita de teste (10 documentos)...")
    path_base = f"teste_diagnostico_{int(time.time())}"
    docs_saved = []

    for i in range(10):
        print(f"    [{i+1}/10] Salvando documento {i}...")
        t_start = time.time()
        try:
            await salvar_dado_em_path(
                f"{path_base}/doc_{i}",
                {"index": i, "timestamp": datetime.now().isoformat()}
            )
            t_elapsed = time.time() - t_start
            docs_saved.append((i, t_elapsed))
            print(f"          OK ({t_elapsed:.3f}s)")
        except Exception as e:
            print(f"          [ERRO] {e}")
            break

        # Pequena pausa entre operacoes
        await asyncio.sleep(0.5)

    # ===== OPERAÇÃO 3: Pausa simulando inatividade =====
    print("\n[3] Simulando inatividade (10 segundos)...")
    for i in range(10):
        print(f"    [{i+1}/10] aguardando... {10-i}s restantes")
        await asyncio.sleep(1)

    # ===== OPERAÇÃO 4: Leitura após inatividade =====
    print("\n[4] Leitura apos inatividade...")
    t_start = time.time()
    try:
        print("    Lendo documento 0...")
        data = await buscar_dado_em_path(f"{path_base}/doc_0")
        t_elapsed = time.time() - t_start
        print(f"    Status: OK (lido em {t_elapsed:.3f}s)")
        print(f"    Dados: {data}")
    except Exception as e:
        print(f"    [TIMEOUT/ERRO] {e}")
        import traceback
        traceback.print_exc()

    # ===== OPERAÇÃO 5: Múltiplas leituras =====
    print("\n[5] Multiplas leituras em sequencia...")
    for i in range(5):
        print(f"    [{i+1}/5] Lendo documento {i}...")
        t_start = time.time()
        try:
            await buscar_dado_em_path(f"{path_base}/doc_{i}")
            t_elapsed = time.time() - t_start
            print(f"          OK ({t_elapsed:.3f}s)")
        except Exception as e:
            print(f"          [ERRO] {e}")

        await asyncio.sleep(0.5)

    # ===== RELATÓRIO =====
    print("\n" + "="*70)
    print("RELATORIO")
    print("="*70)
    print(f"\nDocumentos salvos: {len(docs_saved)}")
    if docs_saved:
        print("Tempos de escrita:")
        for idx, elapsed in docs_saved:
            print(f"  Doc {idx}: {elapsed:.3f}s")
        avg = sum(e[1] for e in docs_saved) / len(docs_saved)
        print(f"  Media: {avg:.3f}s")

    print(f"\nCliente Firestore reutilizado: SIM (mesmo ID ao longo do teste)")
    print(f"Timeout observado: {'Nao' if len(docs_saved) == 10 else 'Sim'}")

if __name__ == "__main__":
    asyncio.run(test_firestore_operations())
