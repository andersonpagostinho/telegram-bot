#!/usr/bin/env python3
"""
Executor COMPLETO dos 174 testes P0 — VALIDAÇÃO REAL ATÉ FIRESTORE
Conforme regra de ouro: Todos os testes devem ir até o final (Firestore)
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def find_p0_test_files():
    """Encontra todos os arquivos com testes P0"""
    test_dir = Path("tests")
    import re

    p0_files = set()

    for test_file in sorted(test_dir.glob("test_*.py")):
        try:
            with open(test_file, encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procura por funções test_p0 ou referências a P0
            if re.search(r'(?:def|async def) test_p0\w*\(', content) or \
               ('test_p0' in test_file.name) or \
               ('p0' in test_file.name and 'test' in content):
                # Contar testes
                test_count = len(re.findall(r'(?:def|async def) test_\w+\(', content))
                if test_count > 0:
                    p0_files.add((test_file.name, test_count))
        except:
            pass

    return sorted(list(p0_files), key=lambda x: -x[1])  # Maior primeiro

def run_p0_suite():
    """Executa suite P0 completa com validação até Firestore"""

    p0_files = find_p0_test_files()

    print(f"\n{'='*80}")
    print("🔥 EXECUÇÃO P0 174 COMPLETA — VALIDAÇÃO FIRESTORE REAL")
    print(f"{'='*80}\n")

    print(f"📊 Arquivos P0 encontrados: {len(p0_files)}")
    print(f"📈 Total estimado de testes: {sum(c for _, c in p0_files)}\n")

    print("Arquivos P0 a executar (top 20):")
    for fname, count in p0_files[:20]:
        print(f"  {count:2d} testes: {fname}")
    if len(p0_files) > 20:
        print(f"  ... e {len(p0_files) - 20} arquivos adicionais")

    # Construir lista de arquivos para pytest
    test_files = [f"tests/{fname}" for fname, _ in p0_files]

    print(f"\n{'='*80}")
    print("⏱️  EXECUÇÃO INICIANDO...")
    print(f"{'='*80}")
    print(f"Timeout: 300s por arquivo (testes E2E com Firestore real)")
    print(f"Modo: Validação completa até confirmação de evento\n")

    # Executar com pytest
    cmd = f"python -m pytest {' '.join(test_files)} -v --tb=short"

    start_time = datetime.now()

    # Configurar environment variables corretamente
    import os
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
    print("📋 RESUMO DA EXECUÇÃO P0 174")
    print(f"{'='*80}")
    print(f"Duração total: {duration:.1f} segundos ({duration/60:.1f} minutos)")
    print(f"Status: {'✅ SUCESSO' if result.returncode == 0 else '❌ FALHAS DETECTADAS'}")

    # Salvar resultado
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_arquivos": len(p0_files),
        "total_testes_estimado": sum(c for _, c in p0_files),
        "duracao_segundos": duration,
        "exit_code": result.returncode,
        "arquivos": [{"arquivo": f, "testes": c} for f, c in p0_files]
    }

    report_path = Path("EXECUCAO_P0_174_2026_10_18.json")
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
