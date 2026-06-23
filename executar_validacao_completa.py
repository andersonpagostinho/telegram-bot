#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Executar validação completa INFRA-03 com logging de resultados
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configurar environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'firebase_credentials.json')

print("\n" + "="*70)
print("VALIDACAO COMPLETA POS INFRA-04")
print("="*70 + "\n")

results = []

tests = [
    ("P1 E2E Identidade", "tests/p1_e2e_onboarding_identidade_real.py", 600),
    ("P1 E2E Operacional", "tests/p1_e2e_onboarding_operacional_completo_real.py", 600),
    ("P1 E2E Individual", "tests/p1_e2e_onboarding_individual_real.py", 600),
    ("P0 Regressao", "tests/runner_p0_regressao_completa.py", 1200),
]

for test_name, test_file, timeout in tests:
    print(f"\n[TESTE] {test_name}")
    print(f"Arquivo: {test_file}")
    print(f"Timeout: {timeout}s")
    print("-" * 70)

    start_time = datetime.now()

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Verificar resultado funcional
        has_pass = "PASS" in stdout or "passed" in stdout.lower()
        has_fail = "FAIL" in stdout or "failed" in stdout.lower()
        has_grpc_timeout = "grpc_wait_for_shutdown_with_timeout" in stderr

        funcional_status = "PASS" if (exit_code == 0 and has_pass) else "FAIL"

        print(f"Exit code: {exit_code}")
        print(f"Duracao: {duration:.1f}s")
        print(f"Status funcional: {funcional_status}")
        print(f"gRPC timeout: {has_grpc_timeout}")

        if has_grpc_timeout:
            # Verificar se o timeout ocorreu APÓS conclusão (durante shutdown)
            if "grpc_wait_for_shutdown_with_timeout() timed out." in stderr:
                grpc_when = "ao shutdown"
            else:
                grpc_when = "durante execucao"
            print(f"gRPC quando: {grpc_when}")
        else:
            grpc_when = "N/A"

        # Classificacao
        if exit_code == 0 and funcional_status == "PASS":
            if has_grpc_timeout:
                classificacao = "PASS (shutdown warning)"
            else:
                classificacao = "PASS"
        elif exit_code == 0:
            classificacao = "PASS COM AVISO"
        else:
            classificacao = "FALHA"

        print(f"Classificacao: {classificacao}")
        print(f"Stdout linhas: {len(stdout.splitlines())}")
        print(f"Stderr linhas: {len(stderr.splitlines())}")

        results.append({
            "teste": test_name,
            "arquivo": test_file,
            "exit_code": exit_code,
            "duracao_s": duration,
            "resultado_funcional": funcional_status,
            "grpc_timeout": has_grpc_timeout,
            "grpc_quando": grpc_when,
            "classificacao": classificacao,
            "stdout_linhas": len(stdout.splitlines()),
            "stderr_linhas": len(stderr.splitlines()),
        })

        # Salvar output para inspecao
        with open(f"resultado_{test_name.replace(' ', '_')}.txt", 'w') as f:
            f.write(f"=== {test_name} ===\n\n")
            f.write(f"Exit code: {exit_code}\n")
            f.write(f"Duracao: {duration:.1f}s\n\n")
            f.write("STDOUT:\n")
            f.write(stdout[-2000:] if len(stdout) > 2000 else stdout)
            f.write("\n\nSTDERR:\n")
            f.write(stderr[-1000:] if len(stderr) > 1000 else stderr)

    except subprocess.TimeoutExpired:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"[TIMEOUT] Teste ultrapassou {timeout}s")
        print(f"Duracao ate timeout: {duration:.1f}s")

        results.append({
            "teste": test_name,
            "arquivo": test_file,
            "exit_code": -1,
            "duracao_s": duration,
            "resultado_funcional": "TIMEOUT",
            "grpc_timeout": None,
            "grpc_quando": "N/A",
            "classificacao": "BLOQUEIO (timeout)",
            "stdout_linhas": 0,
            "stderr_linhas": 0,
        })

    except Exception as e:
        print(f"[ERRO] {str(e)}")
        results.append({
            "teste": test_name,
            "arquivo": test_file,
            "exit_code": -2,
            "duracao_s": 0,
            "resultado_funcional": "ERRO",
            "grpc_timeout": None,
            "grpc_quando": "N/A",
            "classificacao": "BLOQUEIO (erro)",
            "stdout_linhas": 0,
            "stderr_linhas": 0,
        })

# Resumo final
print("\n" + "="*70)
print("RESUMO FINAL")
print("="*70 + "\n")

for r in results:
    print(f"{r['teste']:30} | Exit:{r['exit_code']:3} | {r['classificacao']}")

# Calcular totais
p1_pass = sum(1 for r in results[:3] if r['exit_code'] == 0)
p0_pass = 1 if results[3]['exit_code'] == 0 else 0

print(f"\nP1 E2E: {p1_pass}/3 testes com exit code 0")
print(f"P0: {p0_pass}/1 teste com exit code 0")

# Salvar resultados em JSON
with open("validacao_resultados.json", 'w') as f:
    json.dump(results, f, indent=2)

print("\nResultados salvos em: validacao_resultados.json")

# Determinar se pode rodar cenario 06
p1_all_ok = p1_pass == 3
p0_ok = p0_pass == 1

if p1_all_ok and p0_ok:
    print("\n[OK] P1 E2E (3/3) e P0 (1/1) passaram com exit code 0")
    print("Pronto para rodar cenario 06")
else:
    print(f"\n[BLOQUEIO] P1 E2E {p1_pass}/3, P0 {p0_ok}/1")
    print("Nao pode rodar cenario 06")
    sys.exit(1)
