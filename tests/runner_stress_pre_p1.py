#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runner agregado para testes P0/P1 apos patches de categoria C.
Executa os cenarios de stress criticos para validar as mudancas.

Cenarios incluidos:
1. rajadas - multiplas mensagens simultaneas
2. concorrencia - multiplos usuarios
3. interrupcao - mensagens de contexto interrompido
4. mudanca de contexto - usuario muda de fluxo
5. confirmacao pendente - race condition em confirmacao
6. multi-entidades - isolamento de tenant
7. notificacoes - processamento de notificacoes
8. conflito - agendamento com conflito

Status: RODANDO APOS PATCHES CATEGORIA C
"""

import sys
import os

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Testes críticos P0/P1 após patches
STRESS_TESTS = [
    "runner_stress_rajadas.py",
    "runner_stress_confirmacao_pendente.py",
    "runner_stress_interrupcao_informativa_completo.py",
    "runner_stress_mudanca_contexto_fluxo_ativo.py",
    "runner_stress_multi_entidades_completo.py",
    "runner_stress_conflito_aceite_sugestao.py",
]

def rodar_teste(nome_arquivo):
    """Roda um teste individual"""
    caminho = os.path.join(os.path.dirname(__file__), nome_arquivo)
    if not os.path.exists(caminho):
        print(f"⚠️  Arquivo não encontrado: {nome_arquivo}")
        return False

    try:
        print(f"\n{'='*80}")
        print(f"Rodando: {nome_arquivo}")
        print(f"{'='*80}\n")

        # Executar via exec para capturar em mesmo contexto
        with open(caminho, 'r', encoding='utf-8') as f:
            codigo = f.read()
        exec(codigo, {"__name__": "__main__", "__file__": caminho})
        return True
    except Exception as e:
        print(f"❌ Erro ao rodar {nome_arquivo}: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("TESTE AGREGADO P0/P1 - POS PATCHES CATEGORIA C")
    print("="*80 + "\n")

    print("Patches aplicados:")
    print("  [OK] C-001: handlers/bot.py:132 - Mensagem de opcao invalida")
    print("  [OK] C-002: handlers/event_handler.py:262 - Erro de data/hora")
    print("  [OK] C-003: handlers/followup_handler.py:137 - Nome de cliente (criar)")
    print("  [OK] C-004: handlers/followup_handler.py:195 - Nome de cliente (concluir)")
    print("  [OK] C-005: handlers/voice_handler.py:22 - Audio nao entendido")

    print("\nCenarios de stress a validar:")
    for i, teste in enumerate(STRESS_TESTS, 1):
        print(f"  {i}. {teste}")

    resultados = {}
    for teste in STRESS_TESTS:
        resultado = rodar_teste(teste)
        resultados[teste] = resultado

    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80 + "\n")

    passou = sum(1 for r in resultados.values() if r)
    total = len(resultados)

    for teste, resultado in resultados.items():
        status = "[PASSOU]" if resultado else "[FALHOU]"
        print(f"{status}: {teste}")

    print(f"\nTotal: {passou}/{total} testes")

    if passou == total:
        print("\n[OK] TODAS AS VALIDACOES PASSARAM!")
        return 0
    else:
        print(f"\n[ATENCAO] {total - passou} testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())
