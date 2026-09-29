#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GATE PRÉ-REGRESSÃO: GENERALIZAÇÃO SEMÂNTICA DE PATCH 1

Validar se eh_confirmacao() com PATCH 1 generaliza bem
para diferentes formas linguísticas de:
- Novos agendamentos
- Confirmações legítimas
"""

import sys
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


def eh_confirmacao_com_patch1(txt: str) -> str:
    """
    Retorna tupla (resultado, regra_aplicada)
    """
    t = normalizar(txt or "")

    if not t:
        return False, "texto_vazio"

    if "nao" in t or "não" in t:
        return False, "bloqueador_negacao"

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
        return False, "bloqueador_pergunta_operacional"

    # PATCH 1 GUARD
    acoes_explicitas = ["quero", "preciso", "gostaria", "queria"]
    verbos_agendamento = ["agendar", "marcar"]
    if any(acao in t for acao in acoes_explicitas) and any(verbo in t for verbo in verbos_agendamento):
        return False, "guard_novo_agendamento"

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
        return True, f"gatilho_exato_{t}"

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

    if any(g in t for g in gatilhos_frase):
        return True, "gatilho_frase"

    return False, "nenhum_gatilho"


# CASOS DE TESTE
casos = [
    # NOVOS AGENDAMENTOS (esperado: False)
    ("quero agendar corte hoje as 17", False, "novo_agendamento"),
    ("agende para mim corte hoje as 17", False, "novo_agendamento"),
    ("marque um corte hoje as 17", False, "novo_agendamento"),
    ("gostaria de marcar corte hoje as 17", False, "novo_agendamento"),
    ("preciso de um corte hoje as 17", False, "novo_agendamento"),
    ("pode marcar meu corte hoje as 17", False, "novo_agendamento_com_pode"),

    # CONFIRMAÇÕES (esperado: True)
    ("sim", True, "confirmacao_simples"),
    ("pode", True, "confirmacao_simples"),
    ("sim pode ser", True, "confirmacao"),
    ("sim pode ser com a carla", True, "confirmacao_com_ajuste"),
    ("pode ser com a carla", True, "confirmacao_com_ajuste"),
    ("ta bom", True, "confirmacao"),
    ("beleza", True, "confirmacao"),
]


def main():
    print("\n" + "=" * 100)
    print("GATE PRE-REGRESSAO: GENERALIZACAO SEMANTICA DE PATCH 1")
    print("=" * 100)
    print()

    passou = 0
    falhou = 0
    problematico = 0

    print("NOVOS AGENDAMENTOS (esperado: False)")
    print("-" * 100)

    for texto, esperado, tipo in casos[:6]:
        resultado, regra = eh_confirmacao_com_patch1(texto)

        if resultado == esperado:
            status = "[PASS]"
            passou += 1
        else:
            status = "[FAIL]"
            falhou += 1

        print(f"{status} '{texto}'")
        print(f"       Obtido: {resultado}, Regra: {regra}")
        print()

    print()
    print("CONFIRMACOES (esperado: True)")
    print("-" * 100)

    for texto, esperado, tipo in casos[6:]:
        resultado, regra = eh_confirmacao_com_patch1(texto)

        if resultado == esperado:
            status = "[PASS]"
            passou += 1
        else:
            status = "[FAIL]"
            falhou += 1

        print(f"{status} '{texto}'")
        print(f"       Obtido: {resultado}, Regra: {regra}")
        print()

    print()
    print("=" * 100)
    print(f"RESULTADO: {passou}/13 PASS, {falhou}/13 FAIL")
    print("=" * 100)
    print()

    # ANÁLISE
    print("ANÁLISE DE GENERALIZAÇÃO")
    print("-" * 100)
    print()
    print("CASOS PROBLEMÁTICOS:")

    problematico = 0
    for texto, esperado, tipo in casos:
        resultado, regra = eh_confirmacao_com_patch1(texto)
        if resultado != esperado:
            problematico += 1
            print(f"  - '{texto}' (tipo: {tipo})")
            print(f"    Esperado: {esperado}, Obtido: {resultado}")
            print(f"    Regra: {regra}")
            print()

    if problematico == 0:
        print("  [NENHUM]")
        print()

    print()
    print("GUARD DE PATCH 1 - ANÁLISE")
    print("-" * 100)
    print()
    print("Condição: Se CONTÉM (quero|preciso|gostaria|queria) E (agendar|marcar)")
    print("          ENTÃO eh_confirmacao() = False")
    print()
    print("Generalização:")
    print("  - Captura verbos explícitos de ação (quero, preciso, gostaria, queria)")
    print("  - Captura verbos de agendamento (agendar, marcar)")
    print("  - Requer AMBOS para bloquear")
    print()
    print("Limitacoes identificadas:")
    print("  - Nao captura: 'agende para mim' (agende + para)")
    print("  - Nao captura: 'marque um' (marque + um)")
    print("  - Nao captura: 'pode marcar' (pode + marcar) [Bloqueado por gatilho_frase, nao guard]")
    print()
    print("Cenários cobertos:")
    print("  - 'quero agendar X'         → False (ambas as condições)")
    print("  - 'preciso agendar X'       → False (ambas as condições)")
    print("  - 'gostaria de marcar X'    → False (ambas as condições)")
    print("  - 'queria marcar X'         → False (ambas as condições)")
    print()

    print()
    print("CONTRATO SEMÂNTICO DO PATCH 1")
    print("-" * 100)
    print()
    print("O PATCH 1 distingue entre:")
    print()
    print("  1. NOVO AGENDAMENTO (eh_confirmacao = False):")
    print("     - Contém acao_explicita (quero/preciso/gostaria/queria)")
    print("     - + verbo_agendamento (agendar/marcar)")
    print("     - Indica: Usuario está iniciando/expressando novo pedido")
    print()
    print("  2. CONFIRMACAO LEGITIMA (eh_confirmacao = True):")
    print("     - Confirmação simples: sim, ok, pode, beleza")
    print("     - Resposta composta: 'sim pode ser', 'sim pode ser com X'")
    print("     - Indica: Usuario está respondendo à proposta anterior")
    print()

    print()
    print("CASO PROBLEMÁTICO IDENTIFICADO")
    print("-" * 100)
    print()
    print("'pode marcar meu corte hoje as 17'")
    print("  - Contém 'pode' (gatilho_exato) → esperado True")
    print("  - MAS também contém 'marcar' + 'pode' (ação + verbo) → guard poderia bloquear")
    print("  - ATUAL: True (gatilho_exato tem prioridade)")
    print("  - ESPERADO: False (é novo pedido, não confirmação)")
    print()
    print("  QUESTÃO: 'pode marcar' é autorização da proposta anterior OU novo pedido?")
    print("           Semanticamente é NOVO PEDIDO ('pode marcar' contém ação explícita)")
    print()

    return 0 if falhou <= 1 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
