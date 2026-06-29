"""
RUNNER F3 — TESTES CRÍTICOS BLOQUEANTES

Validar ANTES de continuar para F3A-F3F:
1. F3C (Sessão/Draft/Confirmação) — 6 cenários (incluindo novo F3C-6)
2. F3-GPT-BOUNDARY (Contrato) — 4 cenários

Esses dois blocos devem estar TODO (estrutura) e prontos para implementação.

Status: AGREGADOR PARCIAL (validação de bloqueantes)
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class ResultadoAgregado:
    def __init__(self):
        self.suites = []
        self.total_geral = 0
        self.pass_geral = 0
        self.todo_geral = 0

    def adicionar_suite(self, nome, total, pass_count, todo_count, cenarios):
        self.suites.append({
            "suite": nome,
            "total": total,
            "pass": pass_count,
            "todo": todo_count,
            "cenarios": cenarios
        })
        self.total_geral += total
        self.pass_geral += pass_count
        self.todo_geral += todo_count

    def relatorio(self):
        print("\n" + "="*80)
        print("F3 — TESTES CRÍTICOS BLOQUEANTES (AGREGADO)")
        print("="*80 + "\n")

        for suite in self.suites:
            status_str = "✅ TODO (estrutura pronta)" if suite["todo"] == suite["total"] else "🔄 PARCIAL"
            print(f"\n{suite['suite']}: {suite['pass']}/{suite['total']} PASS ({status_str})")

        print("\n" + "-"*80)
        print(f"TOTAL AGREGADO: {self.pass_geral}/{self.total_geral} PASS")
        print(f"TODO (estrutura): {self.todo_geral} cenários")
        print("-"*80 + "\n")

        if self.todo_geral == self.total_geral:
            print("✅ BLOQUEANTES PRONTOS PARA IMPLEMENTAÇÃO")
            print("   Próximo: Implementar F3C + F3-GPT-BOUNDARY")
            print("   Depois: Criar F3A, F3B, F3D, F3E, F3F")
        else:
            print("⚠️ BLOQUEANTES INCOMPLETOS")
            print(f"   {self.pass_geral} cenários já implementados")
            print(f"   {self.todo_geral} cenários ainda estruturados (TODO)")

        print("\n")


async def executar_f3c():
    """Executar F3C — Sessão/Draft/Confirmação"""
    # Importar dinamicamente para evitar dependências circulares
    try:
        from test_f3c_sessao_confirmacao_real import main as main_f3c
        resultado = await main_f3c()
        return resultado
    except Exception as e:
        print(f"❌ Erro ao executar F3C: {e}")
        return None


async def executar_f3_gpt_boundary():
    """Executar F3-GPT-BOUNDARY — Contrato GPT/Motor"""
    try:
        from test_f3_gpt_boundary_contrato_real import main as main_boundary
        resultado = await main_boundary()
        return resultado
    except Exception as e:
        print(f"❌ Erro ao executar F3-GPT-BOUNDARY: {e}")
        return None


async def main():
    print("\n" + "="*80)
    print("F3 — BLOQUEANTES (PRÉ-REQUISITO PARA F3A-F3F)")
    print("="*80 + "\n")

    print("Executando F3C (Sessão/Draft/Confirmação)...")
    resultado_f3c = await executar_f3c()

    print("\nExecutando F3-GPT-BOUNDARY (Contrato)...")
    resultado_boundary = await executar_f3_gpt_boundary()

    # Agregar resultados
    agregado = ResultadoAgregado()

    if resultado_f3c:
        agregado.adicionar_suite(
            "F3C — Sessão/Draft/Confirmação",
            resultado_f3c["total"],
            resultado_f3c["pass"],
            resultado_f3c["todo"],
            resultado_f3c.get("cenarios", [])
        )

    if resultado_boundary:
        agregado.adicionar_suite(
            "F3-GPT-BOUNDARY — Contrato GPT/Motor",
            resultado_boundary["total"],
            resultado_boundary["pass"],
            resultado_boundary["todo"],
            resultado_boundary.get("cenarios", [])
        )

    # Imprimir relatório
    agregado.relatorio()

    # Retornar resultado agregado
    return {
        "bloqueantes": True,
        "suites_total": len(agregado.suites),
        "cenarios_total": agregado.total_geral,
        "cenarios_pass": agregado.pass_geral,
        "cenarios_todo": agregado.todo_geral,
        "status": "pronto_para_implementacao" if agregado.todo_geral == agregado.total_geral else "incompleto",
        "detalhes": agregado.suites
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())
    print("\n" + "="*80)
    print("RESULTADO FINAL (JSON)")
    print("="*80)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
