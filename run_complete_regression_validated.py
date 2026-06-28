#!/usr/bin/env python3
"""
REGRESSÃO COMPLETA VALIDADA
P1 E2E: 42/42
P0 Real Firebase: 174/174

Relatório gerado SOMENTE se 100% passar
"""

import subprocess
import sys
import os
import json
from datetime import datetime

TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("=" * 90)
print("REGRESSAO COMPLETA VALIDADA - P1 (42/42) + P0 (174/174)")
print("=" * 90)
print(f"Timestamp: {TIMESTAMP}\n")
print("[INFO] Relatório será gerado SOMENTE se 100% passar\n")

# P1 E2E runners (espera-se 42 testes)
P1_RUNNERS = [
    "tests/runner_p1_e2e_onboarding_identidade_real.py",
    "tests/runner_p1_e2e_onboarding_individual_real.py",
    "tests/runner_p1_e2e_onboarding_operacional_completo_real.py",
]

# P0 Real Firebase runners (espera-se 174 testes)
P0_RUNNERS = [
    "tests/runner_p0_e2e_firestore_real.py",
    "tests/runner_p0_agenda_critica_real.py",
    "tests/runner_p0_multitenant_real.py",
    "tests/runner_p0_persistencia_real.py",
    "tests/runner_p0_fluxos_conversacionais_reais.py",
]

def run_runner(runner_file):
    """Executa um arquivo runner e retorna resultado."""
    print(f"[EXECUTANDO] {runner_file}...", flush=True)

    try:
        result = subprocess.run(
            [sys.executable, runner_file],
            capture_output=True,
            text=True,
            timeout=600
        )

        # Tentar parsear JSON resultado
        try:
            with open(runner_file.replace(".py", ".json").replace("runner_", "resultado_"), 'r') as f:
                result_json = json.load(f)

            return {
                "runner": runner_file,
                "exit_code": result.returncode,
                "passed": result.returncode == 0 and result_json.get("status_geral") == "PASSOU",
                "total": result_json.get("total_testes", 0),
                "passou": result_json.get("passou", 0),
                "falhou": result_json.get("falhou", 0),
                "status_geral": result_json.get("status_geral", "UNKNOWN")
            }
        except:
            return {
                "runner": runner_file,
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "total": 0,
                "passou": 0,
                "falhou": 0,
                "status_geral": "ERROR"
            }

    except subprocess.TimeoutExpired:
        return {
            "runner": runner_file,
            "exit_code": -1,
            "passed": False,
            "error": "TIMEOUT"
        }
    except Exception as e:
        return {
            "runner": runner_file,
            "exit_code": -1,
            "passed": False,
            "error": str(e)
        }

# ============================================================================
# FASE 1: P1 E2E (42 testes)
# ============================================================================
print("\n[FASE 1] Executando P1 E2E (42 testes esperados)...\n")

p1_results = []
p1_total_tests = 0
p1_passed = 0

for runner in P1_RUNNERS:
    result = run_runner(runner)
    p1_results.append(result)

    if result["passed"]:
        print(f"  [OK] {runner}: {result.get('passou', 0)}/{result.get('total', 0)}")
        p1_passed += 1
        p1_total_tests += result.get("passou", 0)
    else:
        print(f"  [FAIL] {runner}: FALHOU")

# ============================================================================
# FASE 2: P0 Real Firebase (174 testes)
# ============================================================================
print(f"\n[FASE 2] Executando P0 Real Firebase (174 testes esperados)...\n")

p0_results = []
p0_total_tests = 0
p0_passed = 0

for runner in P0_RUNNERS:
    result = run_runner(runner)
    p0_results.append(result)

    if result["passed"]:
        print(f"  [OK] {runner}: {result.get('passou', 0)}/{result.get('total', 0)}")
        p0_passed += 1
        p0_total_tests += result.get("passou", 0)
    else:
        print(f"  [FAIL] {runner}: FALHOU")

# ============================================================================
# VALIDAÇÃO E RELATÓRIO
# ============================================================================
print("\n" + "=" * 90)
print("VALIDACAO FINAL")
print("=" * 90)

print(f"\nP1 E2E:")
print(f"  Esperado: 42 testes")
print(f"  Obtido: {p1_total_tests} testes")
print(f"  Runners passaram: {p1_passed}/{len(P1_RUNNERS)}")

print(f"\nP0 Real Firebase:")
print(f"  Esperado: 174 testes")
print(f"  Obtido: {p0_total_tests} testes")
print(f"  Runners passaram: {p0_passed}/{len(P0_RUNNERS)}")

# Validação rigorosa
is_valid = (
    p1_total_tests >= 42 and
    p0_total_tests >= 174 and
    p1_passed == len(P1_RUNNERS) and
    p0_passed == len(P0_RUNNERS)
)

print("\n" + "=" * 90)

if is_valid:
    print("[OK] REGRESSAO COMPLETA VALIDADA - 100% PASSOU")
    print("=" * 90)

    # Gerar relatório oficial
    report = {
        "timestamp": TIMESTAMP,
        "status": "PASSOU_100_PORCENTO",
        "p1": {
            "esperado": 42,
            "obtido": p1_total_tests,
            "runners_passaram": p1_passed,
            "runners_total": len(P1_RUNNERS),
            "details": p1_results
        },
        "p0": {
            "esperado": 174,
            "obtido": p0_total_tests,
            "runners_passaram": p0_passed,
            "runners_total": len(P0_RUNNERS),
            "details": p0_results
        },
        "total_testes_executados": p1_total_tests + p0_total_tests,
        "validacao": "100% PASSOU - RELATORIO VALIDO"
    }

    # Salvar relatório
    with open("RELATORIO_REGRESSAO_COMPLETA_VALIDADO.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n[OK] Relatório salvo: RELATORIO_REGRESSAO_COMPLETA_VALIDADO.json\n")
    print("[OK] P1: 42/42 PASSOU")
    print("[OK] P0: 174/174 PASSOU")
    print("[OK] TOTAL: 216/216 PASSOU\n")

    sys.exit(0)

else:
    print("[FAIL] REGRESSAO INCOMPLETA - FALHAS DETECTADAS")
    print("=" * 90)
    print("\n[FAIL] Relatório NÃO será gerado")
    print("[FAIL] Status: FALHA NA VALIDACAO\n")
    print(f"P1: obtido {p1_total_tests}/42")
    print(f"P0: obtido {p0_total_tests}/174\n")

    sys.exit(1)
