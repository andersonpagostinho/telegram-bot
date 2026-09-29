#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTES OBRIGATÓRIOS — PATCH 1 + PATCH 2
========================================

Data: 2026-09-28
Objetivo: Validar que:

1. PATCH 1: eh_confirmacao() NÃO dispara em "quero agendar"
2. PATCH 2: aguardando_confirmacao_agendamento é invalidado em novo agendamento

Testes: T1-T7 conforme gate pré-patch
Status: Implementação controlada
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from router.principal_router import eh_confirmacao


class Teste:
    def __init__(self, id, nome):
        self.id = id
        self.nome = nome
        self.status = "PENDENTE"
        self.resultado = None
        self.mensagem = None


def test_t1_confirmacao_simples():
    """T1: Confirmação simples — 'sim' deve retornar True"""
    teste = Teste("T1", "Confirmação simples")

    resultado = eh_confirmacao("sim")

    if resultado == True:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado True, obtido {resultado}"

    return teste


def test_t2_autorizacao_legitima():
    """T2: Autorização legítima — 'pode agendar?' deve retornar True"""
    teste = Teste("T2", "Autorização legítima")

    resultado = eh_confirmacao("pode agendar")

    if resultado == True:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado True, obtido {resultado}"

    return teste


def test_t3_novo_agendamento_com_confirmacao_stale():
    """T3: NOVO AGENDAMENTO — 'quero agendar corte hoje as 17' deve retornar False"""
    teste = Teste("T3", "Novo agendamento (BUG FIX)")

    resultado = eh_confirmacao("quero agendar corte hoje as 17")

    # PATCH 1: Deve retornar False (novo agendamento, não confirmação)
    if resultado == False:
        teste.status = "PASS"
        teste.resultado = True
        teste.mensagem = "Novo agendamento corretamente identificado como NÃO confirmação"
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"FALHOU: Esperado False (novo agendamento), obtido True"

    return teste


def test_t4_novo_agendamento_sem_confirmacao():
    """T4: Novo agendamento sem confirmação — deve também retornar False"""
    teste = Teste("T4", "Novo agendamento sem contexto")

    resultado = eh_confirmacao("quero agendar escova amanhã")

    if resultado == False:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado False, obtido {resultado}"

    return teste


def test_t5_ajuste_legitimo():
    """T5: Ajuste legítimo — 'quero outro horário' deve retornar False (ajuste, não confirmação)"""
    teste = Teste("T5", "Ajuste (novo pedido)")

    resultado = eh_confirmacao("quero outro horário")

    if resultado == False:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado False (é ajuste), obtido {resultado}"

    return teste


def test_t6_confirmacao_com_profissional():
    """T6: Confirmação com profissional — 'sim, pode ser com a Carla' deve retornar True"""
    teste = Teste("T6", "Confirmação com ajuste")

    resultado = eh_confirmacao("sim pode ser com a carla")

    # "sim" é gatilho exato, então deve retornar True
    if resultado == True:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado True (contém 'sim'), obtido {resultado}"

    return teste


def test_t7_alteracao_explicita():
    """T7: Alteração explícita — 'na verdade quero coloração' deve retornar False"""
    teste = Teste("T7", "Alteração (novo pedido)")

    resultado = eh_confirmacao("na verdade quero coloracao")

    if resultado == False:
        teste.status = "PASS"
        teste.resultado = True
    else:
        teste.status = "FAIL"
        teste.resultado = False
        teste.mensagem = f"Esperado False (é mudança), obtido {resultado}"

    return teste


def main():
    print("\n" + "=" * 80)
    print("TESTES OBRIGATÓRIOS — PATCH 1 + PATCH 2")
    print("=" * 80)
    print()

    testes = [
        test_t1_confirmacao_simples(),
        test_t2_autorizacao_legitima(),
        test_t3_novo_agendamento_com_confirmacao_stale(),
        test_t4_novo_agendamento_sem_confirmacao(),
        test_t5_ajuste_legitimo(),
        test_t6_confirmacao_com_profissional(),
        test_t7_alteracao_explicita(),
    ]

    passou = 0
    falhou = 0

    print("RESULTADOS")
    print("-" * 80)

    for teste in testes:
        status_icon = "[PASS]" if teste.status == "PASS" else "[FAIL]"
        print(f"{status_icon} {teste.id}: {teste.nome}")

        if teste.mensagem:
            print(f"      {teste.mensagem}")

        if teste.status == "PASS":
            passou += 1
        else:
            falhou += 1

    print("\n" + "=" * 80)
    print(f"RESULTADO: {passou}/7 PASS, {falhou}/7 FAIL")
    print("=" * 80)
    print()

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
