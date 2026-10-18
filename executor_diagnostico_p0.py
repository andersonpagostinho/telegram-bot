#!/usr/bin/env python3
"""
Executor diagnóstico de testes P0
- Timeouts reais (300s por teste E2E)
- Coleta detalhada de erros
- Análise de padrões
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def run_diagnostic():
    """Executa diagnóstico completo dos testes P0"""

    test_dir = Path("tests")
    p0_tests = sorted([t for t in test_dir.glob("test_p0*.py")])[:6]  # Primeiros 6 para diagnosticar

    print(f"\n{'='*80}")
    print("🔍 DIAGNÓSTICO DE TESTES P0")
    print(f"{'='*80}")
    print(f"Total de testes a diagnosticar: {len(p0_tests)}")
    print(f"Timeout: 300 segundos por teste")
    print(f"Modo: Coleta detalhada de erros\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_testes": len(p0_tests),
        "testes": [],
        "resumo": {
            "coletados": 0,
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "erro_importacao": 0,
            "padroes_erro": defaultdict(int)
        }
    }

    for idx, test_file in enumerate(p0_tests, 1):
        print(f"\n[{idx}/{len(p0_tests)}] {test_file.name}")
        print(f"{'─'*80}")

        # Coletar testes
        collect_cmd = f"PYTHONIOENCODING=utf-8 python -m pytest {test_file} --collect-only -q 2>&1"
        collect_result = subprocess.run(
            collect_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        collect_output = collect_result.stdout + collect_result.stderr
        num_collected = collect_output.count(" test")

        if num_collected == 0:
            # Verificar se é erro de importação
            if "ImportError" in collect_output or "ModuleNotFoundError" in collect_output:
                print(f"  ❌ ERRO DE IMPORTAÇÃO")
                results["resumo"]["erro_importacao"] += 1
                # Extrair erro
                for line in collect_output.split("\n"):
                    if "Error" in line:
                        print(f"     {line.strip()[:100]}")
                        break
            else:
                print(f"  ⚠️  Nenhum teste coletado")
            continue

        print(f"  ✅ {num_collected} teste(s) coletado(s)")
        results["resumo"]["coletados"] += num_collected

        # Executar testes
        exec_cmd = f"PYTHONIOENCODING=utf-8 python -m pytest {test_file} -v --tb=line 2>&1"

        try:
            exec_result = subprocess.run(
                exec_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos para testes E2E
            )

            output = exec_result.stdout + exec_result.stderr
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")

            print(f"  📊 Resultado: {passed} PASSED | {failed} FAILED")

            results["resumo"]["passed"] += passed
            results["resumo"]["failed"] += failed

            # Extrair mensagem de erro se houver falha
            test_detail = {
                "arquivo": test_file.name,
                "coletados": num_collected,
                "passed": passed,
                "failed": failed,
                "erros": []
            }

            if failed > 0:
                for line in output.split("\n"):
                    if "AssertionError" in line or "assert" in line:
                        erro_msg = line.strip()[:150]
                        test_detail["erros"].append(erro_msg)
                        print(f"     ❌ {erro_msg[:100]}")
                        # Categorizar erro
                        if "Mensagem" in erro_msg:
                            results["resumo"]["padroes_erro"]["Mensagem"] += 1
                        elif "Firestore" in erro_msg:
                            results["resumo"]["padroes_erro"]["Firestore"] += 1
                        else:
                            results["resumo"]["padroes_erro"]["Outro"] += 1
                        break

            results["testes"].append(test_detail)

        except subprocess.TimeoutExpired:
            print(f"  ⏱️  TIMEOUT (>300s)")
            results["resumo"]["timeout"] += 1
            results["testes"].append({
                "arquivo": test_file.name,
                "coletados": num_collected,
                "status": "TIMEOUT"
            })

    # Gerar relatório
    print(f"\n{'='*80}")
    print("📋 RESUMO DIAGNÓSTICO")
    print(f"{'='*80}")
    print(f"[✅] Testes coletados: {results['resumo']['coletados']}")
    print(f"[✅] Testes PASSED: {results['resumo']['passed']}")
    print(f"[❌] Testes FAILED: {results['resumo']['failed']}")
    print(f"[⏱️] Timeouts: {results['resumo']['timeout']}")
    print(f"[🚫] Erros de importação: {results['resumo']['erro_importacao']}")

    if results['resumo']['padroes_erro']:
        print(f"\n[📊] Padrões de Erro:")
        for padrao, count in results['resumo']['padroes_erro'].items():
            print(f"     - {padrao}: {count}")

    # Salvar relatório
    relatorio_path = Path("DIAGNOSTICO_P0_2026_10_18.json")
    with open(relatorio_path, "w", encoding="utf-8") as f:
        # Converter defaultdict
        results["resumo"]["padroes_erro"] = dict(results["resumo"]["padroes_erro"])
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[REPORT] Salvo em: {relatorio_path}")
    return results

if __name__ == "__main__":
    try:
        results = run_diagnostic()
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
