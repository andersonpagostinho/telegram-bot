"""
RUNNER F4 — E2E REAL TENANT NOVO

Agregador que executa F4 E2E Real:
- 1 teste de E2E completo
- 7 clientes em cenários reais
- Validação de persistência
- Limpeza automática

Status: IMPLEMENTAÇÃO
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def executar_f4():
    """Executar teste F4 E2E Real"""
    try:
        from f4_e2e_real.test_f4_e2e_tenant_novo_7_clientes import main
        resultado = await main()
        return resultado
    except Exception as e:
        print(f"  ⚠️ F4 E2E não executado: {e}")
        return None


async def main():
    print("\n" + "="*80)
    print("F4 — E2E REAL (AGREGADOR)")
    print("="*80 + "\n")

    # Executar F4
    print("Executando F4 — E2E Tenant Novo...")
    resultado_f4 = await executar_f4()

    # Relatório
    print("\n" + "="*80)
    print("RESULTADO FINAL (JSON)")
    print("="*80)

    resultado_final = {
        "f4_e2e": resultado_f4 if resultado_f4 else {
            "status": "falha_execucao",
            "clientes_processados": 0,
            "total_clientes": 7
        }
    }

    print(json.dumps(resultado_final, indent=2, ensure_ascii=False))

    return resultado_final


if __name__ == "__main__":
    resultado = asyncio.run(main())
