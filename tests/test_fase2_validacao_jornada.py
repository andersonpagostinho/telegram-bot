#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 2.2 — Testes de Validação de Jornada Individual

Testa:
1. Validação de formato "igual ao salão"
2. Validação de formato "HH:MM-HH:MM"
3. Rejeição de formato inválido
4. Rejeição de início >= fim
5. Normalização de horários
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.onboarding_dono_service import _validar_jornada_profissional


def test_igual_ao_salao():
    """Aceita 'igual' como resposta válida."""
    print("\n" + "="*70)
    print("[T1] Validação: 'igual ao salão'")
    print("="*70)

    testes = [
        ("igual", True),
        ("Igual", True),
        ("IGUAL AO SALÃO", True),
        ("igual ao salao", True),
        ("  igual  ", True),
    ]

    passou = 0
    for valor, esperado in testes:
        resultado = _validar_jornada_profissional(valor)
        status = "✅" if resultado == esperado else "❌"
        print(f"  {status} '{valor}' → {resultado} (esperado: {esperado})")
        if resultado == esperado:
            passou += 1

    print(f"  {passou}/{len(testes)} PASSOU")
    return passou == len(testes)


def test_horario_valido():
    """Aceita formato HH:MM-HH:MM."""
    print("\n" + "="*70)
    print("[T2] Validação: 'HH:MM-HH:MM' válido")
    print("="*70)

    testes = [
        ("09:00-18:00", True),
        ("14:00-17:00", True),
        ("09:00-9:00", False),  # início >= fim
        ("18:00-09:00", False),  # fim < início
        ("09:00-09:00", False),  # início == fim
        ("  14:00-17:00  ", True),  # com espaços
        ("9:00-17:00", True),  # sem zero à esquerda
        ("9-17", True),  # sem minutos
    ]

    passou = 0
    for valor, esperado in testes:
        resultado = _validar_jornada_profissional(valor)
        status = "✅" if resultado == esperado else "❌"
        print(f"  {status} '{valor}' → {resultado} (esperado: {esperado})")
        if resultado == esperado:
            passou += 1

    print(f"  {passou}/{len(testes)} PASSOU")
    return passou == len(testes)


def test_formato_invalido():
    """Rejeita formatos inválidos."""
    print("\n" + "="*70)
    print("[T3] Validação: Formatos inválidos rejeitados")
    print("="*70)

    testes = [
        ("14:00", False),  # sem intervalo
        ("1400-1700", False),  # sem dois-pontos
        ("14:00:1700", False),  # formato errado
        ("25:00-26:00", False),  # horários inválidos
        ("14:60-17:00", False),  # minutos inválidos
        ("abc-def", False),  # não-numérico
        ("", False),  # vazio
        ("    ", False),  # apenas espaços
        ("14:00 17:00", False),  # sem hífen
    ]

    passou = 0
    for valor, esperado in testes:
        resultado = _validar_jornada_profissional(valor)
        status = "✅" if resultado == esperado else "❌"
        print(f"  {status} '{valor}' → {resultado} (esperado: {esperado})")
        if resultado == esperado:
            passou += 1

    print(f"  {passou}/{len(testes)} PASSOU")
    return passou == len(testes)


def main():
    """Executa testes de validação."""
    print("\n" + "="*70)
    print("TESTES DE VALIDAÇÃO — FASE 2.2")
    print("="*70)

    testes = [
        ("'igual ao salão'", test_igual_ao_salao),
        ("'HH:MM-HH:MM' válido", test_horario_valido),
        ("Formatos inválidos", test_formato_invalido),
    ]

    resultados = []
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)

    for nome, resultado in resultados:
        status = "✅" if resultado else "❌"
        print(f"{status} {nome}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    return passou == total


if __name__ == "__main__":
    resultado = main()
    sys.exit(0 if resultado else 1)
