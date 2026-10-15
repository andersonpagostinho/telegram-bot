#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runner P0 — Teste de Gap: "outra profissional"

Executa o teste específico que cobre o gap descoberto em produção via pytest.

Problema: "outra profissional" retornava resposta vazia em produção
Causa: detectar_alteracao_draft_agendamento() retornava None para padrão genérico

Validação: Testes T1-T6 cobrem:
- T1: Padrão genérico retorna {"tipo": "profissional", "valor": None}
- T2: Nome específico continua funcionando
- T3: Abreviações continuam funcionando
- T4: Variações continuam funcionando
- T5: Serviço continua sendo detectado
- T6: Horário continua sendo detectado

Total esperado: 6/6 PASS
"""

import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RESULTADO_JSON = "tests/resultado_p0_outra_profissional_gap.json"


class TestRunnerOutraProfissionalGap:
    """Executor do teste de gap via pytest"""

    def __init__(self):
        self.resultado_json = RESULTADO_JSON

    def executar_testes_pytest(self):
        """Executa testes via pytest"""
        print("\n" + "=" * 80)
        print("RUNNER P0 — TESTE DE GAP: 'outra profissional'")
        print("=" * 80)
        print()

        # Executar pytest
        resultado = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_p0_outra_profissional_gap.py",
             "-v", "--tb=short"],
            capture_output=True,
            text=True
        )

        print(resultado.stdout)
        if resultado.stderr:
            print(resultado.stderr)

        return resultado.returncode == 0

    def extrair_resultado_pytest(self):
        """Extrai resultado dos testes pytest"""
        # Rodar pytest com formato JSON para capturar resultados precisos
        resultado_proc = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_p0_outra_profissional_gap.py",
             "-v", "--tb=no", "-q"],
            capture_output=True,
            text=True
        )

        # Contar PASSED vs FAILED no output
        output = resultado_proc.stdout + resultado_proc.stderr

        # Padrão: "5 passed, 1 failed"
        import re
        match_passed = re.search(r'(\d+) passed', output)
        match_failed = re.search(r'(\d+) failed', output)

        passou = int(match_passed.group(1)) if match_passed else 0
        falhou = int(match_failed.group(1)) if match_failed else 0

        # Se não encontrou, tentar padrão alternativo
        if passou == 0 and falhou == 0:
            passou = 6 if resultado_proc.returncode == 0 else 0
            falhou = 0 if resultado_proc.returncode == 0 else 6

        total = passou + falhou if (passou + falhou) > 0 else 6
        taxa_sucesso = f"{(passou / total * 100) if total > 0 else 0:.1f}%"

        resultado = {
            "suite": "test_p0_outra_profissional_gap",
            "passou": passou,
            "falhou": falhou,
            "total": total,
            "taxa_sucesso": taxa_sucesso,
            "data": datetime.now().isoformat(),
            "descricao": "Teste de gap descoberto em produção: 'outra profissional' genérico retornava vazio",
            "causa_raiz": "detectar_alteracao_draft_agendamento() não reconhecia padrões genéricos",
            "solucao": "Adicionar padrão genérico em linhas 2424-2440 de principal_router.py",
            "validacao": [
                "T1: Padrão genérico retorna {'tipo': 'profissional', 'valor': None}",
                "T2-T4: Variações continuam funcionando",
                "T5-T6: Serviço e horário não foram quebrados",
            ],
            "return_code": resultado_proc.returncode
        }

        return resultado

    def salvar_resultado_json(self, resultado):
        """Salva resultado em JSON"""
        with open(self.resultado_json, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)


def main():
    """Função main para compatibilidade com agregador"""
    runner = TestRunnerOutraProfissionalGap()
    sucesso = runner.executar_testes_pytest()

    # Extrair resultado
    resultado = runner.extrair_resultado_pytest()

    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)

    print(f"\nTotal: {resultado['passou']}/{resultado['passou'] + resultado['falhou']} testes passaram")
    print(f"Taxa de sucesso: {resultado['taxa_sucesso']}\n")

    # Salvar JSON resultado
    runner.salvar_resultado_json(resultado)

    print(f"✅ Resultado salvo em: {RESULTADO_JSON}\n")

    # Exit code
    return 0 if sucesso else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
