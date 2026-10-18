#!/usr/bin/env python3
"""
Executor de testes P0 em lotes de 10
Gera relatorio de erros SEM fazer fixes
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

def run_p0_batches():
    """Executa testes P0 em lotes de 10 e gera relatorio"""

    # Encontrar todos os testes P0
    test_dir = Path("tests")
    p0_tests = sorted(test_dir.glob("test_p0*.py"))

    print(f"\n{'='*80}")
    print(f"EXECUCAO DE TESTES P0 EM LOTES")
    print(f"{'='*80}")
    print(f"\nTotal de testes encontrados: {len(p0_tests)}")
    print(f"Lote: 10 testes por execucao")

    # Resultado
    results = {
        "data": datetime.now().isoformat(),
        "total_testes": len(p0_tests),
        "lotes": [],
        "resumo": {
            "total_passou": 0,
            "total_falhou": 0,
            "testes_com_erro": [],
        }
    }

    # Executar em lotes
    for batch_num, i in enumerate(range(0, len(p0_tests), 10), 1):
        batch = p0_tests[i:i+10]
        test_files = " ".join(str(t) for t in batch)

        print(f"\n{'='*80}")
        print(f"LOTE {batch_num}: Testes {i+1} a {min(i+10, len(p0_tests))}")
        print(f"{'='*80}")

        for test in batch:
            print(f"  - {test.name}")

        # Executar pytest
        print(f"\n[EXECUTANDO LOTE {batch_num}...]")
        cmd = f"PYTHONIOENCODING=utf-8 python -m pytest {test_files} -v --tb=line 2>&1"

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Analisar resultado
        output = result.stdout + result.stderr

        # Contar passa/falha
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")

        print(f"\n[RESULTADO] PASSED: {passed} | FAILED: {failed}")

        # Registrar
        lote = {
            "numero": batch_num,
            "testes": [t.name for t in batch],
            "passaram": passed,
            "falharam": failed,
        }

        # Se houver falhas, registrar
        if failed > 0:
            erros = []
            for line in output.split("\n"):
                if "FAILED" in line:
                    erros.append(line.strip())
            lote["erros"] = erros[:5]  # Primeiros 5 erros
            results["resumo"]["testes_com_erro"].extend(erros)

        results["lotes"].append(lote)
        results["resumo"]["total_passou"] += passed
        results["resumo"]["total_falhou"] += failed

    # Salvar relatorio
    relatorio_path = Path("relatorio_p0_batches.json")
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"RESUMO FINAL")
    print(f"{'='*80}")
    print(f"[PASS] Total PASSOU: {results['resumo']['total_passou']}")
    print(f"[FAIL] Total FALHOU: {results['resumo']['total_falhou']}")
    print(f"[INFO] Total: {results['resumo']['total_passou'] + results['resumo']['total_falhou']}")
    print(f"\n[REPORT] Relatorio salvo: {relatorio_path}")

    if results['resumo']['testes_com_erro']:
        unique_erros = list(set(results['resumo']['testes_com_erro']))
        print(f"\n[ERROR] TESTES COM ERRO ({len(unique_erros)} unicos):")
        for erro in unique_erros[:10]:
            print(f"   - {erro[:100]}...")

    return results

if __name__ == "__main__":
    try:
        results = run_p0_batches()
        sys.exit(0 if results['resumo']['total_falhou'] == 0 else 1)
    except Exception as e:
        print(f"\n[ERROR] Erro ao executar: {e}")
        sys.exit(1)
