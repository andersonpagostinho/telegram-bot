#!/usr/bin/env python3
"""
F8 MVP — RUNNER DE TESTES

Executa suite completa:
- F8-1 a F8-8 (8 cenários)
- Validação de regressão (P0, P1, F1-F4)

Uso:
    python tests/runner_f8_encaixe.py
"""

import subprocess
import sys
from datetime import datetime

def print_header(title):
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def run_command(cmd, description):
    """Execute command and return success status."""
    print(f"\n📋 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    success = result.returncode == 0
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"{status}: {description}")
    return success

def main():
    print_header("F8 MVP — ENCAIXE / LISTA DE ESPERA ATIVA — RUNNER DE TESTES")
    print(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # ========================================================
    # FASE 1: F8 Testes
    # ========================================================
    print_header("FASE 1: Testes F8 (8 cenários)")

    test_cmd = "pytest tests/f8_encaixe/test_f8_lista_espera_real.py -v -s --tb=short"
    results["F8_TESTES"] = run_command(test_cmd, "F8-1 até F8-8 (Firestore real)")

    # ========================================================
    # FASE 2: Regressão P0 (se disponível)
    # ========================================================
    print_header("FASE 2: Regressão P0")

    p0_cmd = "python tests/test_p0_regressao.py" if True else None
    if p0_cmd:
        results["P0_REGRESSAO"] = run_command(p0_cmd, "P0 Regressão (174/174)")
    else:
        print("⚠️  P0 runner não encontrado, pulando")
        results["P0_REGRESSAO"] = None

    # ========================================================
    # FASE 3: Regressão P1 (se disponível)
    # ========================================================
    print_header("FASE 3: Regressão P1")

    p1_cmd = "python tests/test_p1_e2e.py" if True else None
    if p1_cmd:
        results["P1_E2E"] = run_command(p1_cmd, "P1 E2E (42/42)")
    else:
        print("⚠️  P1 runner não encontrado, pulando")
        results["P1_E2E"] = None

    # ========================================================
    # FASE 4: Regressão F1-F4 (se disponível)
    # ========================================================
    print_header("FASE 4: Regressão F1-F4")

    f_cmd = "python tests/test_baseline_f1_f4.py" if True else None
    if f_cmd:
        results["F1_F4_BASELINE"] = run_command(f_cmd, "F1-F4 Baseline (56/56)")
    else:
        print("⚠️  Baseline runner não encontrado, pulando")
        results["F1_F4_BASELINE"] = None

    # ========================================================
    # RESULTADO FINAL
    # ========================================================
    print_header("RESULTADO FINAL")

    total = len([r for r in results.values() if r is not None])
    passou = len([r for r in results.values() if r is True])
    falhou = len([r for r in results.values() if r is False])

    for nome, resultado in results.items():
        if resultado is None:
            status = "⏭️  PULADO"
        elif resultado:
            status = "✅ PASSOU"
        else:
            status = "❌ FALHOU"
        print(f"{status}: {nome}")

    print(f"\n{'='*70}")
    print(f"  TOTAL: {passou}/{total} PASSOU")
    if falhou > 0:
        print(f"  ❌ {falhou} FALHOU")
    print(f"{'='*70}\n")

    # Exit code
    if falhou > 0:
        sys.exit(1)
    elif passou < total:
        sys.exit(0)  # Parcialmente sucesso (alguns pulados)
    else:
        print("✅ TODOS OS TESTES PASSARAM!")
        sys.exit(0)

if __name__ == "__main__":
    main()
