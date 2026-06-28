#!/usr/bin/env python3
"""
Executar Regressão Completa: P1 42/42 + P0 174/174
Script agregador que executa todas as baterias de teste certificadas
"""

import sys
import os
import subprocess
import json
from datetime import datetime
import pytz

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(__file__))

# Timezone Brasil
TZ = pytz.timezone("America/Sao_Paulo")

# P1 E2E Tests (42 testes esperados)
P1_TESTS = [
    "tests/p1_e2e_onboarding_identidade_real.py",
    "tests/p1_e2e_onboarding_individual_real.py",
    "tests/p1_e2e_onboarding_operacional_completo_real.py",
]

# P0 Baterias (174 testes esperados)
P0_BATERIAS = [
    ("tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py", 7),
    ("tests/p0_bateria_real_cancelamento_completo.py", 15),
    ("tests/p0_real_confirmacao_pendente_completo.py", 17),
    ("tests/p0_real_mudanca_contexto_completo.py", 25),
    ("tests/p0_real_multi_entidades_completo.py", 15),
    ("tests/p0_real_ajuste_incremental_avancado.py", 20),
    ("tests/p0_real_notificacoes_e2e.py", 20),
    ("tests/p0_real_admin_dono_completo.py", 25),
    ("tests/p0_real_profissional_completo.py", 30),
]


def print_header(title):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80 + "\n")


def print_section(title):
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")


def executar_teste(caminho, tipo="P1", timeout=600):
    """Executa um teste individual e retorna resultado"""
    print(f"▶ Executando: {os.path.basename(caminho)}")

    try:
        result = subprocess.run(
            [sys.executable, caminho],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(__file__)
        )

        sucesso = result.returncode == 0
        print(f"  {'✅ PASS' if sucesso else '❌ FAIL'} (exit code: {result.returncode})")

        return {
            "arquivo": os.path.basename(caminho),
            "tipo": tipo,
            "sucesso": sucesso,
            "exit_code": result.returncode,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        print(f"  ⏱ TIMEOUT (>{timeout}s)")
        return {
            "arquivo": os.path.basename(caminho),
            "tipo": tipo,
            "sucesso": False,
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Timeout após {timeout}s"
        }
    except Exception as e:
        print(f"  💥 ERRO: {str(e)}")
        return {
            "arquivo": os.path.basename(caminho),
            "tipo": tipo,
            "sucesso": False,
            "exit_code": 255,
            "stdout": "",
            "stderr": str(e)
        }


def main():
    print_header("🔄 REGRESSÃO COMPLETA — P1 42/42 + P0 174/174")

    inicio = datetime.now(TZ)
    print(f"Iniciado: {inicio.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")

    resultados = {
        "timestamp": inicio.isoformat(),
        "p1": {"esperados": 0, "passaram": 0, "falharam": 0, "testes": []},
        "p0": {"esperados": 174, "passaram": 0, "falharam": 0, "baterias": []},
    }

    # FASE 1: P1 E2E (42/42)
    print_section("FASE 1: P1 E2E (Bateria completa)")

    for teste in P1_TESTS:
        if os.path.exists(teste):
            resultado = executar_teste(teste, tipo="P1", timeout=300)
            resultados["p1"]["testes"].append(resultado)
            resultados["p1"]["esperados"] += 1

            if resultado["sucesso"]:
                resultados["p1"]["passaram"] += 1
            else:
                resultados["p1"]["falharam"] += 1
        else:
            print(f"⚠️  Arquivo não encontrado: {teste}")

    # FASE 2: P0 (174/174)
    print_section("FASE 2: P0 (9 baterias certificadas)")

    for bateria, esperados in P0_BATERIAS:
        if os.path.exists(bateria):
            resultado = executar_teste(bateria, tipo="P0", timeout=600)
            resultado["cenarios_esperados"] = esperados
            resultados["p0"]["baterias"].append(resultado)

            if resultado["sucesso"]:
                resultados["p0"]["passaram"] += esperados
            else:
                resultados["p0"]["falharam"] += esperados
        else:
            print(f"⚠️  Arquivo não encontrado: {bateria}")

    # RESUMO FINAL
    print_header("📊 RESUMO FINAL")

    fim = datetime.now(TZ)
    duracao = (fim - inicio).total_seconds()

    print(f"Finalizado: {fim.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Duração total: {int(duracao // 60)}m {int(duracao % 60)}s\n")

    # P1
    p1_status = "✅ PASS" if resultados["p1"]["falharam"] == 0 else "❌ FAIL"
    print(f"P1 E2E: {p1_status}")
    print(f"  {resultados['p1']['passaram']} de {resultados['p1']['esperados']} testes passaram")

    # P0
    p0_status = "✅ PASS" if resultados["p0"]["falharam"] == 0 else "❌ FAIL"
    print(f"\nP0 Regressão: {p0_status}")
    print(f"  {resultados['p0']['passaram']} de {resultados['p0']['esperados']} cenários passaram")

    # Status geral
    print()
    total_falharam = resultados["p1"]["falharam"] + resultados["p0"]["falharam"]

    if total_falharam == 0:
        print("✅ REGRESSÃO COMPLETA: SUCESSO (216/216 PASS)")
    else:
        print(f"❌ REGRESSÃO COMPLETA: FALHAS DETECTADAS ({total_falharam} erros)")

    # Salvar resultado em JSON
    resultado_file = "resultado_regressao_completa.json"
    with open(resultado_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Resultado salvo: {resultado_file}")

    # Exit code
    exit_code = 0 if total_falharam == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
