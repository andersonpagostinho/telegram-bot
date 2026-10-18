#!/usr/bin/env python3
"""
Executor COMPLETO dos 174 testes P0 v2 — VALIDAÇÃO REAL ATÉ FIRESTORE
- Versão corrigida: valida existência de arquivos antes de rodar
"""

import subprocess
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def find_p0_test_files():
    """Encontra todos os arquivos com testes P0 que realmente existem"""
    test_dir = Path("tests")
    p0_files = set()

    for test_file in sorted(test_dir.glob("test_*.py")):
        # Validar que arquivo existe
        if not test_file.exists() or not test_file.is_file():
            continue

        try:
            with open(test_file, encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procura por funções test_p0
            test_count = len(re.findall(r'(?:def|async def) test_p0\w*\(', content))
            if test_count > 0:
                # Arquivo tem testes P0
                p0_files.add((test_file.name, test_count))
        except:
            pass

    return sorted(list(p0_files), key=lambda x: -x[1])

def run_p0_suite():
    """Executa suite P0 completa"""

    p0_files = find_p0_test_files()

    print(f"\n{'='*80}")
    print("🔥 EXECUÇÃO P0 — VALIDAÇÃO FIRESTORE REAL (v2)")
    print(f"{'='*80}\n")

    print(f"📊 Arquivos P0 encontrados (existentes): {len(p0_files)}")
    print(f"📈 Total estimado de testes: {sum(c for _, c in p0_files)}\n")

    print("Arquivos P0 a executar (top 20):")
    for fname, count in p0_files[:20]:
        print(f"  {count:2d} testes: {fname}")
    if len(p0_files) > 20:
        print(f"  ... e {len(p0_files) - 20} arquivos adicionais")

    # Validar que todos os arquivos existem
    test_dir = Path("tests")
    test_files_to_run = []
    missing_files = []

    for fname, _ in p0_files:
        full_path = test_dir / fname
        if full_path.exists():
            test_files_to_run.append(str(full_path))
        else:
            missing_files.append(fname)

    if missing_files:
        print(f"\n⚠️  Arquivos listados mas não encontrados ({len(missing_files)}):")
        for f in missing_files[:5]:
            print(f"  ❌ {f}")
        if len(missing_files) > 5:
            print(f"  ... e {len(missing_files) - 5} adicionais")

    print(f"\n{'='*80}")
    print("⏱️  EXECUÇÃO INICIANDO...")
    print(f"{'='*80}")
    print(f"Arquivos com testes: {len(test_files_to_run)}")
    print(f"Modo: Validação completa até Firestore\n")

    if not test_files_to_run:
        print("❌ Nenhum arquivo de teste encontrado!")
        return 1

    # Executar com pytest
    cmd = f"python -m pytest {' '.join(test_files_to_run)} -v --tb=short"

    start_time = datetime.now()

    # Configurar environment
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    result = subprocess.run(
        cmd,
        shell=True,
        cwd=".",
        env=env,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*80}")
    print("📋 RESUMO DA EXECUÇÃO P0")
    print(f"{'='*80}")
    print(f"Duração total: {duration:.1f} segundos ({duration/60:.1f} minutos)")
    print(f"Status: {'✅ SUCESSO' if result.returncode == 0 else '❌ FALHAS'}")

    # Salvar resultado
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_arquivos": len(test_files_to_run),
        "total_testes_estimado": sum(c for _, c in p0_files),
        "duracao_segundos": duration,
        "exit_code": result.returncode,
        "arquivos": [{"arquivo": f.split("/")[-1], "path": f} for f in test_files_to_run]
    }

    report_path = Path("EXECUCAO_P0_COMPLETO_2026_10_18.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[REPORT] Salvo em: {report_path}\n")

    return result.returncode

if __name__ == "__main__":
    try:
        exit_code = run_p0_suite()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERRO FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
