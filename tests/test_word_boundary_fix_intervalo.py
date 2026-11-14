#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST: Word Boundary Fix para extração de intervalo horário

Validar que a correção \b(?:até|ate)\b não captura "ate" dentro de "tarde"
e continua capturando o limite verdadeiro.

9 casos de teste obrigatórios + validação de fluxo completo.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multisservico_service import extrair_intervalo_horario


def test_case(numero, descricao, mensagem, inicio_esperado, fim_esperado):
    """Executar um caso de teste"""
    inicio, fim = extrair_intervalo_horario(mensagem)

    status_inicio = "PASS" if inicio == inicio_esperado else "FAIL"
    status_fim = "PASS" if fim == fim_esperado else "FAIL"

    print(f"\n[CASO {numero}] {descricao}")
    print(f"  Mensagem: {mensagem[:80]}...")
    print(f"  Esperado: ({inicio_esperado}, {fim_esperado})")
    print(f"  Obtido:   ({inicio}, {fim})")
    print(f"  Status:   {status_inicio} / {status_fim}")

    return (status_inicio == "PASS" and status_fim == "PASS")


async def main():
    print("=" * 70)
    print("TEST SUITE: Word Boundary Fix - Extração de Intervalo")
    print("=" * 70)

    resultados = []

    # CASO 1: Mensagem integral de produção (14/11/2026)
    caso1 = test_case(
        1,
        "Mensagem integral produção 14/11 (tarde + até real)",
        "Gostaria de verificar manicure e pedicure para segunda-feira, dia 16/11/2026, de preferencia no mesmo atendimento, durante o periodo da tarde. Consigo chegar a partir das 14h, mas tenho um compromisso no final do dia e preciso terminar os dois servicos ate, no maximo, 17h.",
        14,
        17
    )
    resultados.append(("CASO 1: Produção 14/11 (tarde + ate real)", caso1))

    # CASO 2: Apenas início
    caso2 = test_case(
        2,
        "Apenas 'a partir das 14h' (sem fim)",
        "Consigo chegar a partir das 14h",
        14,
        None
    )
    resultados.append(("CASO 2: Apenas início", caso2))

    # CASO 3: Apenas fim
    caso3 = test_case(
        3,
        "Apenas 'até 17h' (sem início)",
        "preciso terminar ate 17h",
        None,
        17
    )
    resultados.append(("CASO 3: Apenas fim", caso3))

    # CASO 4: Fim com modificador
    caso4 = test_case(
        4,
        "'até, no máximo, 17h' (com modificador)",
        "preciso terminar ate, no maximo, 17h",
        None,
        17
    )
    resultados.append(("CASO 4: Fim com modificador", caso4))

    # CASO 5: Sem confundir com "tarde"
    caso5 = test_case(
        5,
        "Palavra 'tarde' NÃO captura como limite, apenas 'até' real",
        "durante a tarde, atendimento a partir das 14h ate 17h",
        14,
        17
    )
    resultados.append(("CASO 5: Não confundir 'tarde'", caso5))

    # CASO 6: Sem acento
    caso6 = test_case(
        6,
        "'ate' sem acento (equivalente a 'até')",
        "preciso estar pronto ate 17h",
        None,
        17
    )
    resultados.append(("CASO 6: Sem acento 'ate'", caso6))

    # CASO 7: Com hora em formato HH:00
    caso7 = test_case(
        7,
        "'até às 17:00' com minutos",
        "preciso terminar ate as 17:00",
        None,
        17
    )
    resultados.append(("CASO 7: Formato HH:00", caso7))

    # CASO 8: Com quebra de linha (teste de normalizacao)
    caso8 = test_case(
        8,
        "Com quebra de linha entre 'até' e hora",
        "preciso terminar\nate, no maximo,\n17h",
        None,
        17
    )
    resultados.append(("CASO 8: Com quebra de linha", caso8))

    # CASO 9: Ambos início e fim contínuos
    caso9 = test_case(
        9,
        "'das 14 às 17' (formato contínuo)",
        "Atendimento das 14 as 17",
        14,
        17
    )
    resultados.append(("CASO 9: Formato contínuo", caso9))

    # RESUMO
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)

    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    falhou = total - passou

    for descricao, resultado in resultados:
        status = "PASS" if resultado else "FAIL"
        print(f"  [{status}] {descricao}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    if falhou == 0:
        print("\n✓ TODOS OS TESTES PASSARAM")
        return 0
    else:
        print(f"\n✗ {falhou} TESTE(S) FALHARAM")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
