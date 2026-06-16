#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGREGADOR DE TESTES P0 — Regressão Crítica de Agendamento

Executa TODOS os runners P0 de forma sequencial e consolida resultados.

Runners executados:
1. runner_regressao_p0_agendamento_critico.py ← Principal
2. runner_stress_negativos_agendamento_p0.py
3. runner_stress_confirmacao_agendamento.py (opcional)
4. runner_stress_confirmacao_pendente_ajustes.py (opcional)
5. runner_stress_conflito_aceite_confirmacao_final.py (opcional)

Critério: Se qualquer runner falhar, retorna exit code 1.
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RUNNERS = [
    "tests/runner_regressao_p0_agendamento_critico.py",
    "tests/runner_stress_negativos_agendamento_p0.py",
    # Opcional — só executar se existir
    # "tests/runner_stress_confirmacao_agendamento.py",
    # "tests/runner_stress_confirmacao_pendente_ajustes.py",
    # "tests/runner_stress_conflito_aceite_confirmacao_final.py",
]

RESULTADO_AGREGADO = "tests/resultado_p0_regressions.json"


def executar_runner(runner_path: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    Executa um runner individual e extrai resultado.

    Retorna: (sucesso: bool, dados: dict, output: str)
    """
    runner_name = Path(runner_path).stem

    try:
        print(f"\n{'='*80}")
        print(f"Executando: {runner_name}")
        print(f"{'='*80}")

        # Executar runner
        resultado = subprocess.run(
            ["python", runner_path],
            capture_output=True,
            text=True,
            cwd="."
        )

        output = resultado.stdout
        print(output)

        # Determinar sucesso (exit code 0 = sucesso)
        sucesso = resultado.returncode == 0

        # Tentar carregar JSON resultado
        json_file = runner_path.replace(".py", "").replace("runner_", "resultado_") + ".json"
        dados = {}

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                dados = json.load(f)
                dados["arquivo_resultado"] = json_file
        except FileNotFoundError:
            dados = {
                "suite": runner_name,
                "erro": f"Arquivo de resultado não encontrado: {json_file}",
                "exit_code": resultado.returncode
            }
        except json.JSONDecodeError:
            dados = {
                "suite": runner_name,
                "erro": "Erro ao decodificar JSON",
                "exit_code": resultado.returncode
            }

        return sucesso, dados, output

    except FileNotFoundError:
        print(f"❌ Runner não encontrado: {runner_path}")
        return False, {"suite": runner_name, "erro": "Arquivo não encontrado"}, ""
    except Exception as e:
        print(f"❌ Erro ao executar {runner_name}: {str(e)}")
        return False, {"suite": runner_name, "erro": str(e)}, ""


def consolidar_resultados(resultados: List[Tuple[str, bool, Dict[str, Any]]]) -> Dict[str, Any]:
    """Consolida resultados de todos os runners."""

    total_passou = 0
    total_falhou = 0
    total_executados = 0
    sucesso_geral = True

    runners_data = []

    for runner_name, sucesso, dados in resultados:
        total_executados += 1

        # Extrair métricas
        passou = dados.get("passou", 0)
        falhou = dados.get("falhou", 0)

        total_passou += passou
        total_falhou += falhou

        if not sucesso:
            sucesso_geral = False

        runners_data.append({
            "runner": runner_name,
            "sucesso": sucesso,
            "passou": passou,
            "falhou": falhou,
            "taxa_sucesso": dados.get("taxa_sucesso", "N/A"),
            "arquivo_resultado": dados.get("arquivo_resultado", ""),
            "erro": dados.get("erro"),
        })

    resultado_consolidado = {
        "agregador": "run_p0_regressions",
        "data": datetime.now().isoformat(),
        "total_runners": total_executados,
        "total_testes": total_passou + total_falhou,
        "total_passou": total_passou,
        "total_falhou": total_falhou,
        "taxa_sucesso_geral": f"{(total_passou / (total_passou + total_falhou) * 100) if (total_passou + total_falhou) > 0 else 0:.1f}%",
        "sucesso_geral": sucesso_geral,
        "runners": runners_data,
        "resumo": {
            "objetivo": "Agregar resultados de todos os testes P0",
            "conclusion": f"{total_passou}/{total_passou + total_falhou} testes passaram",
            "status": "✅ SUCESSO" if sucesso_geral else "❌ FALHA"
        }
    }

    return resultado_consolidado


def main():
    """Executa agregador de testes P0."""

    print("\n" + "=" * 80)
    print("AGREGADOR DE TESTES P0 — REGRESSÃO CRÍTICA DE AGENDAMENTO")
    print("=" * 80)
    print(f"\nRunners a executar: {len(RUNNERS)}")
    for runner in RUNNERS:
        print(f"  • {runner}")

    resultados = []

    # Executar cada runner
    for runner_path in RUNNERS:
        sucesso, dados, output = executar_runner(runner_path)
        runner_name = Path(runner_path).stem
        resultados.append((runner_name, sucesso, dados))

    # Consolidar resultados
    consolidado = consolidar_resultados(resultados)

    # Imprimir resumo
    print("\n" + "=" * 80)
    print("RESUMO CONSOLIDADO P0")
    print("=" * 80 + "\n")

    print(f"Total de runners: {consolidado['total_runners']}")
    print(f"Total de testes: {consolidado['total_testes']}")
    print(f"Testes que passaram: {consolidado['total_passou']}")
    print(f"Testes que falharam: {consolidado['total_falhou']}")
    print(f"Taxa de sucesso geral: {consolidado['taxa_sucesso_geral']}")
    print(f"\nStatus: {consolidado['resumo']['status']}\n")

    # Tabela por runner
    print("Resultado por Runner:\n")
    print(f"{'Runner':<50} {'Passou':<12} {'Falhou':<12} {'Status':<10}")
    print("-" * 84)
    for runner_info in consolidado['runners']:
        status = "✅ OK" if runner_info['sucesso'] else "❌ FALHA"
        passou = runner_info.get('passou', 0)
        falhou = runner_info.get('falhou', 0)
        print(f"{runner_info['runner']:<50} {passou:<12} {falhou:<12} {status:<10}")

    # Salvar JSON consolidado
    with open(RESULTADO_AGREGADO, "w", encoding="utf-8") as f:
        json.dump(consolidado, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultado consolidado salvo em: {RESULTADO_AGREGADO}\n")

    # Retornar exit code
    return 0 if consolidado['sucesso_geral'] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
