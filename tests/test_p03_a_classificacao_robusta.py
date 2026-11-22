#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.3-A — Testes de Classificação Robusta

Valida que as 4 operações são classificadas corretamente.
Critério crítico: Frase real retorna CONSULTA_DISPONIBILIDADE, não INDEFINIDO.
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.classificador_conversa import classificar_operacao_robusta


def test_p03_a_consulta_disponibilidade_frase_real():
    """
    P0.3-A — Teste Crítico: Frase real deve ser CONSULTA_DISPONIBILIDADE
    """
    resultado = classificar_operacao_robusta(
        "Queria cortar o cabelo segunda às 16 teria horário?"
    )
    assert resultado == "CONSULTA_DISPONIBILIDADE", \
        f"Frase real retornou '{resultado}', esperado 'CONSULTA_DISPONIBILIDADE'"
    print("✅ PASS: Frase real → CONSULTA_DISPONIBILIDADE")


def test_p03_a_consulta_disponibilidade_variacao_1():
    """Variação: Pergunta com temporal"""
    resultado = classificar_operacao_robusta(
        "Pode marcar segunda às 16?"
    )
    assert resultado == "CONSULTA_DISPONIBILIDADE", \
        f"Retornou '{resultado}', esperado 'CONSULTA_DISPONIBILIDADE'"
    print("✅ PASS: 'Pode marcar segunda às 16?' → CONSULTA_DISPONIBILIDADE")


def test_p03_a_consulta_disponibilidade_variacao_2():
    """Variação: Dúvida com temporal"""
    resultado = classificar_operacao_robusta(
        "Teria horário hoje à tarde?"
    )
    assert resultado == "CONSULTA_DISPONIBILIDADE", \
        f"Retornou '{resultado}', esperado 'CONSULTA_DISPONIBILIDADE'"
    print("✅ PASS: 'Teria horário hoje à tarde?' → CONSULTA_DISPONIBILIDADE")


def test_p03_a_agendamento_direto():
    """AGENDAMENTO: Intenção + temporal, sem dúvida"""
    resultado = classificar_operacao_robusta(
        "Quero corte segunda às 16"
    )
    assert resultado == "AGENDAMENTO", \
        f"Retornou '{resultado}', esperado 'AGENDAMENTO'"
    print("✅ PASS: 'Quero corte segunda às 16' → AGENDAMENTO")


def test_p03_a_agendamento_direto_com_profissional():
    """AGENDAMENTO: Com profissional específico"""
    resultado = classificar_operacao_robusta(
        "quero corte segunda as 10 com bruna"
    )
    assert resultado == "AGENDAMENTO", \
        f"Retornou '{resultado}', esperado 'AGENDAMENTO'"
    print("✅ PASS: 'quero corte segunda as 10 com bruna' → AGENDAMENTO")


def test_p03_a_agendamento_marcar():
    """AGENDAMENTO: Verbo marcar"""
    resultado = classificar_operacao_robusta(
        "Marcar corte quinta às 15"
    )
    assert resultado == "AGENDAMENTO", \
        f"Retornou '{resultado}', esperado 'AGENDAMENTO'"
    print("✅ PASS: 'Marcar corte quinta às 15' → AGENDAMENTO")


def test_p03_a_consulta_informativa_sem_temporal():
    """CONSULTA_INFORMATIVA: Apenas pergunta"""
    resultado = classificar_operacao_robusta(
        "Bruna atende corte?"
    )
    assert resultado == "CONSULTA_INFORMATIVA", \
        f"Retornou '{resultado}', esperado 'CONSULTA_INFORMATIVA'"
    print("✅ PASS: 'Bruna atende corte?' → CONSULTA_INFORMATIVA")


def test_p03_a_consulta_informativa_servico():
    """CONSULTA_INFORMATIVA: Pergunta sobre serviço"""
    resultado = classificar_operacao_robusta(
        "Vocês fazem escova?"
    )
    assert resultado == "CONSULTA_INFORMATIVA", \
        f"Retornou '{resultado}', esperado 'CONSULTA_INFORMATIVA'"
    print("✅ PASS: 'Vocês fazem escova?' → CONSULTA_INFORMATIVA")


def test_p03_a_indefinido_incompleto():
    """INDEFINIDO: Sem marcadores claros"""
    resultado = classificar_operacao_robusta(
        "Oi"
    )
    assert resultado == "INDEFINIDO", \
        f"Retornou '{resultado}', esperado 'INDEFINIDO'"
    print("✅ PASS: 'Oi' → INDEFINIDO")


def test_p03_a_indefinido_sem_temporal():
    """INDEFINIDO: Intenção mas sem temporal"""
    resultado = classificar_operacao_robusta(
        "Quero corte"
    )
    assert resultado == "INDEFINIDO", \
        f"Retornou '{resultado}', esperado 'INDEFINIDO'"
    print("✅ PASS: 'Quero corte' → INDEFINIDO")


def test_p03_a_continuidade_fluxo_ativo():
    """Continuidade: Com fluxo ativo retorna AGENDAMENTO"""
    ctx = {"estado_fluxo": "aguardando_profissional"}
    resultado = classificar_operacao_robusta(
        "Sim, aceito",
        ctx=ctx
    )
    assert resultado == "AGENDAMENTO", \
        f"Retornou '{resultado}', esperado 'AGENDAMENTO' (continuidade)"
    print("✅ PASS: Fluxo ativo → AGENDAMENTO (continuidade)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 P0.3-A — Testes de Classificação Robusta")
    print("=" * 70 + "\n")

    tests = [
        test_p03_a_consulta_disponibilidade_frase_real,
        test_p03_a_consulta_disponibilidade_variacao_1,
        test_p03_a_consulta_disponibilidade_variacao_2,
        test_p03_a_agendamento_direto,
        test_p03_a_agendamento_direto_com_profissional,
        test_p03_a_agendamento_marcar,
        test_p03_a_consulta_informativa_sem_temporal,
        test_p03_a_consulta_informativa_servico,
        test_p03_a_indefinido_incompleto,
        test_p03_a_indefinido_sem_temporal,
        test_p03_a_continuidade_fluxo_ativo,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {test.__name__}")
            print(f"   {str(e)}\n")
            failed += 1

    print("=" * 70)
    print(f"\n📊 RESULTADO: {passed} PASS / {failed} FAIL (Total: {len(tests)})\n")

    if failed == 0:
        print("✅ TODOS OS TESTES PASSARAM\n")
        sys.exit(0)
    else:
        print(f"❌ {failed} TESTE(S) FALHARAM\n")
        sys.exit(1)
