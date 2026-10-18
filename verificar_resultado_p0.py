#!/usr/bin/env python3
"""
Script para verificar resultado da execução P0 174
Roda após pytest terminar
"""

import json
from pathlib import Path
import time

def wait_for_result(timeout=1800):
    """Aguarda resultado do arquivo JSON (máx 30 min)"""

    report_path = Path("EXECUCAO_P0_174_2026_10_18.json")
    pytest_output = Path("pytest_output.log")

    print("\n🔍 AGUARDANDO RESULTADO DA EXECUÇÃO P0 174...")
    print(f"Arquivo esperado: {report_path}")
    print(f"Timeout: {timeout}s ({timeout/60:.0f} minutos)\n")

    start = time.time()
    while time.time() - start < timeout:
        if report_path.exists() and report_path.stat().st_size > 100:
            # Arquivo gerado, tentar ler
            try:
                with open(report_path) as f:
                    data = json.load(f)

                print("="*80)
                print("✅ RESULTADO DISPONÍVEL")
                print("="*80)
                print(f"Total de arquivos testados: {data.get('total_arquivos', '?')}")
                print(f"Total de testes estimado: {data.get('total_testes_estimado', '?')}")
                print(f"Duração: {data.get('duracao_segundos', 0):.1f} segundos")
                print(f"Status saída: {data.get('exit_code', 'N/A')}")

                if data.get('exit_code') == 0:
                    print("\n✅ SUCESSO! Todos os testes passaram!")
                else:
                    print("\n⚠️ FALHAS DETECTADAS. Verifique o log completo.")

                print(f"\nArquivos com testes:")
                for item in data.get('arquivos', [])[:10]:
                    print(f"  {item['testes']:2d} testes: {item['arquivo']}")

                if len(data.get('arquivos', [])) > 10:
                    print(f"  ... e {len(data['arquivos']) - 10} arquivos adicionais")

                return True

            except (json.JSONDecodeError, KeyError) as e:
                pass  # Arquivo ainda sendo escrito

        # Mostrar progresso
        elapsed = time.time() - start
        if int(elapsed) % 30 == 0:
            print(f"⏳ Aguardando... ({elapsed:.0f}s)")

        time.sleep(2)

    print(f"\n❌ TIMEOUT! Resultado não disponível após {timeout}s")
    return False

if __name__ == "__main__":
    import sys
    success = wait_for_result(timeout=1800)  # 30 minutos max
    sys.exit(0 if success else 1)
