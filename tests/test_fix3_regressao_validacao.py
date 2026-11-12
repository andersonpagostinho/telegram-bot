#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação de regressões do Fix 3

Testa casos de confirmação legítima que NÃO devem ser afetados
"""

import sys
sys.path.insert(0, '.')

from router.principal_router import eh_confirmacao, tem_confirmacao_temporal_condicional
from utils.normalizador_humano import normalizar_intencao_humana


def test_confirmacoes_legitimas():
    """Validar que confirmações imediatas continuam funcionando"""

    casos_legit = [
        ("Sim", True),
        ("sim", True),
        ("OK", True),
        ("ok", True),
        ("Certo", True),
        ("certo", True),
        ("Perfeito", True),
        ("Beleza", True),
        ("Pode confirmar", True),
        ("Pode marcar", True),
        ("Pode agendar", True),
        ("Confirmo", True),
        ("Confirma", True),
        ("Confirme", True),
        ("Funciona", True),
        ("Tá bom", True),
        ("Isso mesmo", True),
        ("Está certo", True),
    ]

    print("\n" + "="*80)
    print("TESTE REGRESSÃO: Confirmações Legítimas")
    print("="*80)

    passed = 0
    failed = 0

    for mensagem, esperado in casos_legit:
        resultado = eh_confirmacao(mensagem)
        status = "✅ PASS" if resultado == esperado else "❌ FAIL"

        if resultado == esperado:
            passed += 1
        else:
            failed += 1

        print(f"{status} | '{mensagem}' → {resultado} (esperado {esperado})")

    print(f"\nResultado Regressão: {passed} PASS / {failed} FAIL")
    return failed == 0


def test_confirmacoes_futuras():
    """Validar que confirmações futuras agora retornam False"""

    casos_futuros = [
        ("Depois que você me apresentar, eu confirmo", False),
        ("Quando encontrar, autorizo", False),
        ("Assim que escolher, confirmo", False),
        ("Logo que apresentar, eu aprovo", False),
        ("Uma vez que eu escolha, confirmo", False),
        ("Depois quando você tiver, confirmo", False),
    ]

    print("\n" + "="*80)
    print("TESTE NOVO: Confirmações Futuras Bloqueadas")
    print("="*80)

    passed = 0
    failed = 0

    for mensagem, esperado in casos_futuros:
        resultado = eh_confirmacao(mensagem)
        temporal = tem_confirmacao_temporal_condicional(mensagem)
        status = "✅ PASS" if resultado == esperado else "❌ FAIL"

        if resultado == esperado:
            passed += 1
        else:
            failed += 1

        print(f"{status} | '{mensagem}' → {resultado} (esperado {esperado}) | temporal_condicional={temporal}")

    print(f"\nResultado Futuras: {passed} PASS / {failed} FAIL")
    return failed == 0


def test_negacoes():
    """Validar que negações retornam False"""

    casos_negacao = [
        ("Não confirme", False),
        ("Não confirmo", False),
        ("Não quero", False),
    ]

    print("\n" + "="*80)
    print("TESTE REGRESSÃO: Negações")
    print("="*80)

    passed = 0
    failed = 0

    for mensagem, esperado in casos_negacao:
        resultado = eh_confirmacao(mensagem)
        status = "✅ PASS" if resultado == esperado else "❌ FAIL"

        if resultado == esperado:
            passed += 1
        else:
            failed += 1

        print(f"{status} | '{mensagem}' → {resultado} (esperado {esperado})")

    print(f"\nResultado Negações: {passed} PASS / {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    results = []

    results.append(("Confirmações Legítimas", test_confirmacoes_legitimas()))
    results.append(("Confirmações Futuras", test_confirmacoes_futuras()))
    results.append(("Negações", test_negacoes()))

    print("\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)

    for nome, resultado in results:
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"{status} | {nome}")

    all_passed = all(r[1] for r in results)

    print("\n" + ("="*80))
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM — Fix 3 validado!")
        print("="*80)
        sys.exit(0)
    else:
        print("❌ ALGUNS TESTES FALHARAM — Revisar Fix 3")
        print("="*80)
        sys.exit(1)
