#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTES UNITÁRIOS — Corração intervalo_fim

Validar que extrair_intervalo_horario() captura corretamente:
1. "até 17h" → fim=17
2. "até, no máximo, 17h" → fim=17
3. "até às 17:00" → fim=17
4. Mensagem real do cenário multisserviço
5. Casos negativos (datas não são confundidas)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multisservico_service import extrair_intervalo_horario


def test_ate_simples():
    """Teste 1: 'até 17h' simples"""
    msg = "preciso terminar até 17h"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 1: Simples 'até 17h'")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU")


def test_ate_com_virgula():
    """Teste 2: 'até, no máximo, 17h' com vírgula"""
    msg = "preciso terminar até, no máximo, 17h"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 2: Com virgula 'até, no máximo, 17h'")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU")


def test_ate_com_as():
    """Teste 3: 'até às 17:00' com crase e minutos"""
    msg = "preciso voltar até às 17:00"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 3: Com crase 'até às 17:00'")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU")


def test_mensagem_real_completa():
    """Teste 4: Mensagem real completa do cenário multisserviço"""
    msg = (
        "Gostaria de agendar manicure e pedicure para sexta-feira, dia 13/11/2026, "
        "a partir das 14h, mas preciso terminar os dois serviços até, no máximo, 17h."
    )
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 4: Mensagem real completa")
    print(f"  Mensagem: '{msg[:80]}...'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert inicio == 14, f"Esperado inicio=14, obtido {inicio}"
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU — Ambos inicio e fim corretos")


def test_data_nao_confundida():
    """Teste 5: Data (13/11) não é confundida com fim"""
    msg = "dia 13/11/2026 até 17h"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 5: Data não confundida com fim")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    # Esperado: fim=17 (não 13 ou 11 da data)
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    assert inicio is None, f"Não deve capturar inicio de data"
    print(f"  ✓ PASSOU — Data não confundida")


def test_sem_limite_final():
    """Teste 6: Mensagem sem limite final"""
    msg = "agendar para sexta-feira a partir de 14h"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 6: Sem limite final")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert inicio == 14, f"Esperado inicio=14, obtido {inicio}"
    assert fim is None, f"Esperado fim=None, obtido {fim}"
    print(f"  ✓ PASSOU — Fim corretamente None")


def test_padrao_1_continuado():
    """Teste 7: PADRÃO 1 (continuado) ainda funciona"""
    msg = "das 14 às 17"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 7: PADRÃO 1 continuado (das X às Y)")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert inicio == 14, f"Esperado inicio=14, obtido {inicio}"
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU — PADRÃO 1 não afetado")


def test_ate_com_espacos_multiplos():
    """Teste 8: 'até' com múltiplos espaços"""
    msg = "até    17h"
    inicio, fim = extrair_intervalo_horario(msg)

    print(f"\nTeste 8: Com múltiplos espaços 'até    17h'")
    print(f"  Mensagem: '{msg}'")
    print(f"  Resultado: inicio={inicio}, fim={fim}")
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"  ✓ PASSOU")


def main():
    print("\n" + "="*70)
    print("TESTES UNITÁRIOS — CORRECAO INTERVALO_FIM")
    print("="*70)

    testes = [
        test_ate_simples,
        test_ate_com_virgula,
        test_ate_com_as,
        test_mensagem_real_completa,
        test_data_nao_confundida,
        test_sem_limite_final,
        test_padrao_1_continuado,
        test_ate_com_espacos_multiplos,
    ]

    falhados = []
    for teste in testes:
        try:
            teste()
        except AssertionError as e:
            print(f"  ✗ FALHOU: {e}")
            falhados.append(teste.__name__)
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
            falhados.append(teste.__name__)

    print("\n" + "="*70)
    if not falhados:
        print(f"✓ RESULTADO: {len(testes)}/{len(testes)} TESTES PASSARAM")
        print("="*70)
        return True
    else:
        print(f"✗ RESULTADO: {len(testes) - len(falhados)}/{len(testes)} PASSARAM, {len(falhados)} FALHARAM")
        print(f"Falhados: {falhados}")
        print("="*70)
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
