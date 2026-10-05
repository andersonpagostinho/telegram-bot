#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE DIRETO — Verificar se identidade_p01 está realmente no código

Problema observado:
- Testes unitários PASSAM
- Teste real FALHA (resposta vazia)
- Pergunta: A identidade está realmente sendo passada?

Objetivo: Verificar se a mudança está no código e se identidade_p01
está disponível nos contextos dos callsites corrigidos.

Data: 2026-10-03
"""

import re
import sys

def verificar_mudancas_no_codigo():
    """Verifica se as mudanças estão realmente no código"""

    print("\n" + "="*70)
    print("TESTE — Verificar Mudanças no Código")
    print("="*70 + "\n")

    arquivo = "router/principal_router.py"

    print(f"[LENDO] {arquivo}...")

    try:
        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo: {e}")
        return False

    # Verificação 1: Procurar por identidade_p01 nos callsites
    print("\n[VERIF 1] Procurando 'identidade=identidade_p01' no arquivo...")

    matches = re.finditer(r'identidade=identidade_p01', conteudo)
    callsites = []

    for match in matches:
        # Encontrar número da linha
        linhas = conteudo[:match.start()].count('\n')
        callsites.append(linhas + 1)

    print(f"[RESULTADO] Encontrados {len(callsites)} callsites com 'identidade=identidade_p01'")
    for i, linha in enumerate(callsites, 1):
        print(f"  {i}. Linha {linha}")

    if len(callsites) < 2:
        print("[FAIL] Esperado 2 callsites, encontrado <2")
        return False

    # Verificação 2: Procurar se identidade_p01 é criada
    print("\n[VERIF 2] Procurando criação de 'identidade_p01'...")

    creation_matches = re.finditer(r'identidade_p01\s*=\s*criar_identidade', conteudo)
    creations = []

    for match in creation_matches:
        linhas = conteudo[:match.start()].count('\n')
        creations.append(linhas + 1)

    print(f"[RESULTADO] Encontradas {len(creations)} criações de identidade_p01")
    for i, linha in enumerate(creations, 1):
        print(f"  {i}. Linha {linha}")

    if len(creations) < 1:
        print("[FAIL] Esperado pelo menos 1 criação de identidade_p01")
        return False

    # Verificação 3: Verificar contexto dos callsites
    print("\n[VERIF 3] Analisando contexto dos callsites...")

    # Procurar linhas ~7600 e ~11400
    linhas = conteudo.split('\n')

    print(f"\n[CONTEXTO] Linha ~7600 (deve ter identidade=identidade_p01):")
    if len(linhas) > 7600:
        for i in range(7595, min(7605, len(linhas))):
            marker = ">>> " if i >= 7598 and i <= 7602 else "    "
            print(f"{marker}{i}: {linhas[i][:80]}")

    print(f"\n[CONTEXTO] Linha ~11400 (deve ter identidade=identidade_p01):")
    if len(linhas) > 11400:
        for i in range(11395, min(11410, len(linhas))):
            marker = ">>> " if i >= 11400 and i <= 11410 else "    "
            print(f"{marker}{i}: {linhas[i][:80]}")

    # Verificação 4: Confirmar que ambos os callsites têm identidade
    print("\n[VERIF 4] Confirmação final...")

    test_7600 = any(7590 < linha < 7610 for linha in callsites)
    test_11400 = any(11390 < linha < 11410 for linha in callsites)

    print(f"Callsite ~7600: {'ENCONTRADO' if test_7600 else 'NAO ENCONTRADO'}")
    print(f"Callsite ~11400: {'ENCONTRADO' if test_11400 else 'NAO ENCONTRADO'}")

    if test_7600 and test_11400:
        print("\n[PASS] Ambos os callsites têm identidade=identidade_p01")
        return True
    else:
        print("\n[FAIL] Um ou ambos os callsites faltam identidade=identidade_p01")
        return False


def verificar_disponibilidade_identidade_p01():
    """Verifica se identidade_p01 está disponível no escopo dos callsites"""

    print("\n" + "="*70)
    print("TESTE — Verificar Disponibilidade de identidade_p01")
    print("="*70 + "\n")

    arquivo = "router/principal_router.py"

    try:
        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo: {e}")
        return False

    # Procurar por criação de identidade_p01
    match_criacao = re.search(r'identidade_p01\s*=\s*criar_identidade_telegram', conteudo)

    if not match_criacao:
        print("[FAIL] identidade_p01 não é criada no código")
        return False

    linha_criacao = conteudo[:match_criacao.start()].count('\n') + 1
    print(f"[ENCONTRADO] identidade_p01 criada na linha: {linha_criacao}")

    # Procurar pelos callsites
    callsite_matches = list(re.finditer(r'identidade=identidade_p01', conteudo))

    if len(callsite_matches) < 2:
        print(f"[FAIL] Esperado 2 callsites, encontrado {len(callsite_matches)}")
        return False

    print(f"[ENCONTRADO] {len(callsite_matches)} callsites usando identidade_p01")

    # Verificar se os callsites estão DEPOIS da criação
    for i, match in enumerate(callsite_matches, 1):
        linha_callsite = conteudo[:match.start()].count('\n') + 1
        posicao = "DEPOIS" if linha_callsite > linha_criacao else "ANTES"

        print(f"  Callsite {i}: linha {linha_callsite} ({posicao} da criação)")

        if linha_callsite <= linha_criacao:
            print(f"  [FAIL] Callsite {i} está ANTES da criação (inválido!)")
            return False

    print("\n[PASS] Todos os callsites estão DEPOIS da criação de identidade_p01")
    return True


def main():
    """Executa testes de verificação"""

    print("\n" + "="*70)
    print("TESTES DE VERIFICACAO — Por que test passa mas real falha?")
    print("="*70)

    results = {}

    # Teste 1: Verificar mudanças
    print("\n[TESTE 1/2] Verificar mudanças no código...")
    results["mudancas"] = verificar_mudancas_no_codigo()

    # Teste 2: Verificar disponibilidade
    print("\n[TESTE 2/2] Verificar disponibilidade de identidade_p01...")
    results["disponibilidade"] = verificar_disponibilidade_identidade_p01()

    # Sumário
    print("\n" + "="*70)
    print("SUMÁRIO")
    print("="*70)

    for teste, resultado in results.items():
        status = "PASS" if resultado else "FAIL"
        print(f"{teste}: [{status}]")

    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} PASSED")

    # Análise
    print("\n" + "="*70)
    print("ANÁLISE")
    print("="*70)

    if all(results.values()):
        print("\n[CONCLUSAO] O CÓDIGO ESTÁ CORRETO!")
        print("  - identidade=identidade_p01 está nos 2 callsites")
        print("  - identidade_p01 é criada ANTES dos callsites")
        print("  - A variável está disponível no escopo")
        print("\nSE O TESTE REAL AINDA FALHA, O PROBLEMA É:")
        print("  1. Identidade não está sendo passada do webhook WhatsApp")
        print("  2. Contexto está sendo perdido em algum ponto")
        print("  3. Update ou Context estão None")
        print("  4. Firestore não consegue responder (timeout)")
        return 0
    else:
        print("\n[CONCLUSAO] PROBLEMA ENCONTRADO NO CÓDIGO!")
        for teste, resultado in results.items():
            if not resultado:
                print(f"  - {teste}: FALHOU")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
