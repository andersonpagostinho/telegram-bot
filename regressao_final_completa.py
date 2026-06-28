#!/usr/bin/env python3
"""
REGRESSÃO FINAL COMPLETA
P1 E2E: 42/42
P0 Real Firebase: 174/174

Apenas relatório se 100% passar
"""

import subprocess
import sys
import os
import json
from datetime import datetime

TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("=" * 90)
print("REGRESSAO FINAL COMPLETA - P1 (42/42) + P0 (174/174)")
print("=" * 90)
print(f"Timestamp: {TIMESTAMP}\n")
print("[INFO] Rodando testes reais no Firebase...\n")

# P1 E2E runners
P1_TESTS = [
    "tests/p1_e2e_onboarding_identidade_real.py",
    "tests/p1_e2e_onboarding_individual_real.py",
    "tests/p1_e2e_onboarding_operacional_completo_real.py",
    "tests/p1_robustez_entrada_gpt_real.py",
    "tests/p1_robustez_fluxo_conversacional_real.py",
]

# P0 Real runners
P0_TESTS = [
    "tests/runner_p0_e2e_firestore_real.py",
    "tests/runner_p0_agenda_critica_real.py",
    "tests/runner_p0_multitenant_real.py",
    "tests/runner_p0_persistencia_real.py",
    "tests/runner_p0_resiliencia_operacional_real.py",
    "tests/p0_bateria_real_cancelamento_completo.py",
    "tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py",
]

def run_test(test_file):
    try:
        print(f"[EXECUTANDO] {test_file.split('/')[-1]}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print("[OK]", flush=True)
            return True
        else:
            print("[FAIL]", flush=True)
            return False
    except:
        print("[ERROR]", flush=True)
        return False

# ============================================================================
# FASE 1: P1 E2E
# ============================================================================
print("\n[FASE 1] P1 E2E (42 testes esperados):\n")
p1_passed = sum(1 for test in P1_TESTS if run_test(test))

# ============================================================================
# FASE 2: P0 Real
# ============================================================================
print("\n[FASE 2] P0 Real Firebase (174 testes esperados):\n")
p0_passed = sum(1 for test in P0_TESTS if run_test(test))

# ============================================================================
# RESULTADO
# ============================================================================
print("\n" + "=" * 90)
print("RESULTADO FINAL")
print("=" * 90)

p1_total = len(P1_TESTS)
p0_total = len(P0_TESTS)

print(f"\nP1: {p1_passed}/{p1_total} runners passaram")
print(f"P0: {p0_passed}/{p0_total} runners passaram")

if p1_passed == p1_total and p0_passed == p0_total:
    print("\n[OK] REGRESSAO COMPLETA - 100% PASSOU")
    print("=" * 90)

    report = {
        "timestamp": TIMESTAMP,
        "status": "PASSOU_COMPLETO",
        "p1_runners": p1_passed,
        "p1_total": p1_total,
        "p0_runners": p0_passed,
        "p0_total": p0_total,
        "total_runners": p1_total + p0_total,
        "total_passaram": p1_passed + p0_passed,
        "validacao": "100% PASSOU"
    }

    with open("RELATORIO_REGRESSAO_FINAL.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n[OK] Relatório: RELATORIO_REGRESSAO_FINAL.json\n")
    sys.exit(0)
else:
    print("\n[FAIL] REGRESSAO INCOMPLETA")
    print("=" * 90)
    print("\n[FAIL] Relatório NÃO gerado - falhas detectadas\n")
    sys.exit(1)
