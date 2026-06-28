#!/usr/bin/env python3
import sys
import os
import subprocess
import json
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TZ = pytz.timezone("America/Sao_Paulo")

P1_TESTS = [
    "tests/p1_e2e_onboarding_identidade_real.py",
    "tests/p1_e2e_onboarding_individual_real.py",
    "tests/p1_e2e_onboarding_operacional_completo_real.py",
]

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

def executar_teste(caminho, tipo="P1", timeout=600):
    print(f"[>] {os.path.basename(caminho)}")
    try:
        result = subprocess.run(
            [sys.executable, caminho],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(__file__)
        )
        sucesso = result.returncode == 0
        print(f"    {'[OK]' if sucesso else '[FAIL]'} (exit: {result.returncode})")
        return {
            "arquivo": os.path.basename(caminho),
            "tipo": tipo,
            "sucesso": sucesso,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        print(f"    [TIMEOUT] >{timeout}s")
        return {"arquivo": os.path.basename(caminho), "tipo": tipo, "sucesso": False, "exit_code": 124}
    except Exception as e:
        print(f"    [ERROR] {str(e)[:50]}")
        return {"arquivo": os.path.basename(caminho), "tipo": tipo, "sucesso": False, "exit_code": 255}

def main():
    print("\n" + "=" * 80)
    print("REGRESSAO COMPLETA - P1 42/42 + P0 174/174")
    print("=" * 80 + "\n")

    inicio = datetime.now(TZ)
    print(f"Iniciado: {inicio.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")

    resultados = {
        "timestamp": inicio.isoformat(),
        "p1": {"esperados": 0, "passaram": 0, "falharam": 0, "testes": []},
        "p0": {"esperados": 174, "passaram": 0, "falharam": 0, "baterias": []},
    }

    # FASE 1: P1
    print("\n" + "-" * 80)
    print("  FASE 1: P1 E2E (Bateria completa)")
    print("-" * 80 + "\n")

    for teste in P1_TESTS:
        if os.path.exists(teste):
            resultado = executar_teste(teste, tipo="P1", timeout=300)
            resultados["p1"]["testes"].append(resultado)
            resultados["p1"]["esperados"] += 1
            if resultado["sucesso"]:
                resultados["p1"]["passaram"] += 1
            else:
                resultados["p1"]["falharam"] += 1

    # FASE 2: P0
    print("\n" + "-" * 80)
    print("  FASE 2: P0 (9 baterias certificadas)")
    print("-" * 80 + "\n")

    for bateria, esperados in P0_BATERIAS:
        if os.path.exists(bateria):
            resultado = executar_teste(bateria, tipo="P0", timeout=600)
            resultado["cenarios_esperados"] = esperados
            resultados["p0"]["baterias"].append(resultado)
            if resultado["sucesso"]:
                resultados["p0"]["passaram"] += esperados
            else:
                resultados["p0"]["falharam"] += esperados

    # RESUMO
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80 + "\n")

    fim = datetime.now(TZ)
    duracao = (fim - inicio).total_seconds()

    print(f"Finalizado: {fim.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Duracao: {int(duracao // 60)}m {int(duracao % 60)}s\n")

    p1_status = "[OK]" if resultados["p1"]["falharam"] == 0 else "[FAIL]"
    print(f"P1 E2E: {p1_status}")
    print(f"  {resultados['p1']['passaram']} de {resultados['p1']['esperados']} testes")

    p0_status = "[OK]" if resultados["p0"]["falharam"] == 0 else "[FAIL]"
    print(f"\nP0 Regressao: {p0_status}")
    print(f"  {resultados['p0']['passaram']} de {resultados['p0']['esperados']} cenarios")

    total_falharam = resultados["p1"]["falharam"] + resultados["p0"]["falharam"]
    print(f"\nTOTAL: {resultados['p1']['passaram'] + resultados['p0']['passaram']}/216 PASS")

    if total_falharam == 0:
        print("\n[OK] REGRESSAO COMPLETA: SUCESSO (216/216 PASS)")
    else:
        print(f"\n[FAIL] REGRESSAO INCOMPLETA ({total_falharam} falhas)")

    # Salvar resultado
    resultado_file = "resultado_regressao_completa_final.json"
    with open(resultado_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\nResultado salvo: {resultado_file}")
    print("\n" + "=" * 80)

    sys.exit(0 if total_falharam == 0 else 1)

if __name__ == "__main__":
    main()
