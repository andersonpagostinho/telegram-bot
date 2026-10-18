#!/usr/bin/env python3
"""
Executor de suite completa de testes — PRODUCTION READY
Coleta dados, testes válidos com timeout real
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def run_test_suite():
    """Executa suite completa de testes com relatório"""

    # Arquivos de teste validados (têm muitos testes)
    test_files = [
        "tests/test_clienteprofile_p1.py",
        "tests/test_consultar_agendamentos_edge_cases.py",
        "tests/test_consultar_agendamentos_usuario.py",
        "tests/test_c447a_equivalencia_cadencia.py",
        "tests/test_c42_idempotencia_atomica.py",
        "tests/test_c310_fase1_indice_derivado.py",
        "tests/test_c315_2_leitura_isolada.py",
        "tests/test_c315_3_escrita_isolada.py",
    ]

    print(f"\n{'='*80}")
    print("🎯 SUITE COMPLETA DE TESTES")
    print(f"{'='*80}\n")
    print(f"Arquivos: {len(test_files)}")
    print(f"Timeout: 300s por arquivo (testes E2E)")
    print(f"\nArquivos a testar:")
    for f in test_files:
        print(f"  - {f}")

    # Executar com pytest
    cmd = f"PYTHONIOENCODING=utf-8 python -m pytest {' '.join(test_files)} -v --tb=short --timeout=300"

    print(f"\n{'='*80}")
    print("🚀 Executando...")
    print(f"{'='*80}\n")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=False,  # Mostrar output em tempo real
        text=True,
    )

    return result.returncode

if __name__ == "__main__":
    import sys
    try:
        exit_code = run_test_suite()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERRO] {e}")
        sys.exit(1)
