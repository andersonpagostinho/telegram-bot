#!/usr/bin/env python3
"""
Executor robusto de testes P0 em lotes de 10 com coleta de erros
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

def run_p0_tests_batches():
    """Executa testes P0 em lotes de 10"""

    test_dir = Path("tests")
    p0_tests = sorted([t for t in test_dir.glob("test_p*.py") if "p0" in t.name])

    print(f"\n{'='*80}")
    print("EXECUCAO DE TESTES P0 - LOTES DE 10")
    print(f"{'='*80}")
    print(f"Total de arquivos: {len(p0_tests)}")
    print(f"Divididos em: {(len(p0_tests) + 9) // 10} lotes\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_arquivos": len(p0_tests),
        "lotes": [],
        "resumo": {
            "total_passed": 0,
            "total_failed": 0,
            "total_errors": 0,
            "arquivos_com_erro": []
        }
    }

    # Executar em lotes
    for batch_num, i in enumerate(range(0, len(p0_tests), 10), 1):
        batch = p0_tests[i:i+10]
        batch_end = min(i+10, len(p0_tests))

        print(f"\n{'='*80}")
        print(f"LOTE {batch_num}: Arquivos {i+1} a {batch_end} / {len(p0_tests)}")
        print(f"{'='*80}")

        for test in batch:
            print(f"  {test.name}")

        # Executar cada arquivo
        batch_result = {
            "numero": batch_num,
            "arquivos": [t.name for t in batch],
            "passed": 0,
            "failed": 0,
            "erros": []
        }

        for test_file in batch:
            cmd = f"PYTHONIOENCODING=utf-8 python -m pytest {test_file} -v 2>&1"

            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                output = result.stdout + result.stderr
                passed = output.count(" PASSED")
                failed = output.count(" FAILED")

                batch_result["passed"] += passed
                batch_result["failed"] += failed
                results["resumo"]["total_passed"] += passed
                results["resumo"]["total_failed"] += failed

                status = "[PASS]" if failed == 0 else "[FAIL]"
                print(f"  {status} {test_file.name} - {passed} PASSED, {failed} FAILED")

                if failed > 0:
                    # Coletar erros
                    erros = [line.strip() for line in output.split("\n") if "FAILED" in line]
                    batch_result["erros"].extend(erros[:3])
                    results["resumo"]["arquivos_com_erro"].append({
                        "arquivo": test_file.name,
                        "erros": erros[:2]
                    })

            except subprocess.TimeoutExpired:
                batch_result["failed"] += 1
                batch_result["erros"].append(f"TIMEOUT: {test_file.name}")
                results["resumo"]["total_errors"] += 1
                print(f"  [TIMEOUT] {test_file.name}")

            except Exception as e:
                batch_result["erros"].append(f"ERROR: {str(e)}")
                results["resumo"]["total_errors"] += 1
                print(f"  [ERROR] {test_file.name}: {str(e)}")

        results["lotes"].append(batch_result)
        print(f"\n[LOTE {batch_num}] Resultado: {batch_result['passed']} PASSED | {batch_result['failed']} FAILED")

    # Salvar relatório
    relatorio_path = Path("relatorio_p0_lotes.json")
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Imprimir resumo
    print(f"\n{'='*80}")
    print("RESUMO FINAL")
    print(f"{'='*80}")
    total = results["resumo"]["total_passed"] + results["resumo"]["total_failed"] + results["resumo"]["total_errors"]
    print(f"[PASS] Total PASSOU: {results['resumo']['total_passed']}")
    print(f"[FAIL] Total FALHOU: {results['resumo']['total_failed']}")
    print(f"[ERROR] Total ERRO: {results['resumo']['total_errors']}")
    print(f"[INFO] Total: {total}")
    print(f"\n[REPORT] Relatorio: {relatorio_path}")

    if results["resumo"]["arquivos_com_erro"]:
        print(f"\n[ARQUIVOS COM ERRO] ({len(results['resumo']['arquivos_com_erro'])}):")
        for item in results["resumo"]["arquivos_com_erro"][:10]:
            print(f"  - {item['arquivo']}")
            for erro in item.get("erros", [])[:1]:
                print(f"    {erro[:80]}...")

    return results

if __name__ == "__main__":
    try:
        results = run_p0_tests_batches()
        print(f"\n[DONE] Execucao concluida")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        sys.exit(1)
