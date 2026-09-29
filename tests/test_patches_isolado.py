#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTES ISOLADOS — PATCH 1 + PATCH 2
====================================

Testa eh_confirmacao() sem dependências externas.
"""

import sys
import re
from pathlib import Path


def normalizar(txt):
    """Normaliza texto como em principal_router.py"""
    if not txt:
        return ""
    t = txt.lower().strip()
    t = t.replace("ã", "a").replace("á", "a").replace("â", "a")
    t = t.replace("é", "e").replace("ê", "e")
    t = t.replace("í", "i")
    t = t.replace("ó", "o").replace("ô", "o")
    t = t.replace("ú", "u")
    t = t.replace("ç", "c")
    return t


def eh_confirmacao_novo(txt: str) -> bool:
    """
    Nova versão com PATCH 1 aplicado.
    Confirmação genérica (sem depender de comando).
    Evita falso positivo em perguntas como "pode ver?".
    """
    t = normalizar(txt or "")

    if not t:
        return False

    if "nao" in t or "não" in t:
        return False

    perguntas_operacionais = [
        "pode ver",
        "pode verificar",
        "pode olhar",
        "pode consultar",
        "pode checar",
        "pode conferir",
        "tem como",
        "consegue ver",
        "consegue verificar",
    ]

    if any(p in t for p in perguntas_operacionais):
        return False

    # PATCH 1: Guard para novo agendamento
    acoes_explicitas = ["quero", "preciso", "gostaria", "queria"]
    verbos_agendamento = ["agendar", "marcar"]
    if any(acao in t for acao in acoes_explicitas) and any(verbo in t for verbo in verbos_agendamento):
        return False

    gatilhos_exatos = {
        "sim",
        "ok",
        "certo",
        "perfeito",
        "beleza",
        "blz",
        "confirmo",
        "confirmado",
        "pode",
        "pode ser",
        "pode sim",
        "pode ir",
        "manda ver",
        "fechar",
    }

    if t in gatilhos_exatos:
        return True

    gatilhos_frase = [
        "pode agendar",
        "pode marcar",
        "pode confirmar",
        "confirmar",
        "confirma",
        "confirme",
        "agende",
        "marque",
    ]

    return any(g in t for g in gatilhos_frase)


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

    resultado = eh_confirmacao_novo("sim")

    if resultado == True:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado True, obtido {resultado}"

    return teste


def test_t2_autorizacao_legitima():
    """T2: Autorização legítima — 'pode agendar?' deve retornar True"""
    teste = Teste("T2", "Autorização legítima")

    resultado = eh_confirmacao_novo("pode agendar")

    if resultado == True:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado True, obtido {resultado}"

    return teste


def test_t3_novo_agendamento_com_confirmacao_stale():
    """T3: NOVO AGENDAMENTO — 'quero agendar corte hoje as 17' deve retornar False"""
    teste = Teste("T3", "Novo agendamento (BUG FIX)")

    resultado = eh_confirmacao_novo("quero agendar corte hoje as 17")

    if resultado == False:
        teste.status = "PASS"
        teste.mensagem = "[PASS] PATCH 1 FUNCIONA: Novo agendamento não é tratado como confirmação"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"[FAIL] PATCH 1 FALHOU: Esperado False, obtido True"

    return teste


def test_t4_novo_agendamento_sem_confirmacao():
    """T4: Novo agendamento sem confirmação — deve também retornar False"""
    teste = Teste("T4", "Novo agendamento sem contexto")

    resultado = eh_confirmacao_novo("quero agendar escova amanhã")

    if resultado == False:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado False, obtido {resultado}"

    return teste


def test_t5_ajuste_legitimo():
    """T5: Ajuste legítimo — 'quero outro horário' deve retornar False"""
    teste = Teste("T5", "Ajuste (novo pedido)")

    resultado = eh_confirmacao_novo("quero outro horário")

    if resultado == False:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado False, obtido {resultado}"

    return teste


def test_t6_confirmacao_com_profissional():
    """T6: Confirmação com profissional — 'sim, pode ser com a Carla' deve retornar True"""
    teste = Teste("T6", "Confirmação com ajuste")

    resultado = eh_confirmacao_novo("sim pode ser com a carla")

    if resultado == True:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado True, obtido {resultado}"

    return teste


def test_t7_alteracao_explicita():
    """T7: Alteração explícita — 'na verdade quero coloração' deve retornar False"""
    teste = Teste("T7", "Alteração (novo pedido)")

    resultado = eh_confirmacao_novo("na verdade quero coloracao")

    if resultado == False:
        teste.status = "PASS"
    else:
        teste.status = "FAIL"
        teste.mensagem = f"Esperado False, obtido {resultado}"

    return teste


def main():
    print("\n" + "=" * 80)
    print("TESTES ISOLADOS — PATCH 1: eh_confirmacao()")
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
            print(f"   {teste.mensagem}")

        if teste.status == "PASS":
            passou += 1
        else:
            falhou += 1

    print("\n" + "=" * 80)
    print(f"RESULTADO: {passou}/7 PASS, {falhou}/7 FAIL")
    print("=" * 80)
    print()

    if falhou == 0:
        print("[OK] PATCH 1 VALIDADO COM SUCESSO")
        print()

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
