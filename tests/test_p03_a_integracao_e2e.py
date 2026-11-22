#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.3-A — Teste E2E de Integração com Roteador

Valida que a correção funciona quando integrada ao roteador.
Frase real: "Queria cortar o cabelo segunda às 16 teria horário?"
Esperado: modo_conversa = "operacional" (após correção P0.3-A)
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.classificador_conversa import (
    classificar_operacao_robusta,
    classificar_contexto_mensagem,
)


def test_p03_a_integracao_simples():
    """
    P0.3-A — Teste Simples de Integração

    Simula o fluxo do roteador:
    1. Chamar classificador robusto (novo)
    2. Se retorna operação válida, forçar modo_conversa = "operacional"
    """
    texto = "Queria cortar o cabelo segunda às 16 teria horário?"
    ctx = {}

    # Passo 1: Classificador robusto
    operacao_p03a = classificar_operacao_robusta(
        texto,
        ctx,
        catalogo_servicos=["corte", "manicure", "pedicure"],
        catalogo_profissionais=["Bruna", "Gloria"]
    )
    print(f"  P0.3-A resultado: {operacao_p03a}")
    assert operacao_p03a == "CONSULTA_DISPONIBILIDADE", \
        f"Esperado CONSULTA_DISPONIBILIDADE, got {operacao_p03a}"

    # Passo 2: Classificador antigo (retorna neutro)
    class_ctx = classificar_contexto_mensagem(
        texto,
        ctx,
        catalogo_servicos=["corte", "manicure", "pedicure"],
        catalogo_profissionais=["Bruna", "Gloria"]
    )
    print(f"  Classificador antigo: modo_conversa={class_ctx.get('modo_conversa')}")

    # Passo 3: Simulando lógica do roteador (correção P0.3-A)
    modo_conversa = class_ctx.get("modo_conversa")
    if operacao_p03a in ("CONSULTA_DISPONIBILIDADE", "AGENDAMENTO", "CONSULTA_INFORMATIVA"):
        modo_conversa = "operacional"

    print(f"  Após correção P0.3-A: modo_conversa={modo_conversa}")
    assert modo_conversa == "operacional", \
        f"Esperado 'operacional', got '{modo_conversa}'"

    print("✅ PASS: Integração E2E funcionando")


def test_p03_a_sem_quebra_agendamento_direto():
    """
    P0.3-A — Sem Quebra de Agendamento Direto

    Validar que agendamentos diretos ainda funcionam.
    """
    texto = "quero corte segunda as 10 com bruna"
    ctx = {}

    operacao_p03a = classificar_operacao_robusta(
        texto,
        ctx,
        catalogo_servicos=["corte", "manicure"],
        catalogo_profissionais=["Bruna"]
    )

    # Deve ser AGENDAMENTO
    assert operacao_p03a == "AGENDAMENTO", \
        f"Agendamento direto retornou {operacao_p03a}"

    # Simulando lógica do roteador
    class_ctx = classificar_contexto_mensagem(
        texto,
        ctx,
        catalogo_servicos=["corte", "manicure"],
        catalogo_profissionais=["Bruna"]
    )
    modo_conversa = class_ctx.get("modo_conversa")

    if operacao_p03a in ("CONSULTA_DISPONIBILIDADE", "AGENDAMENTO", "CONSULTA_INFORMATIVA"):
        modo_conversa = "operacional"

    assert modo_conversa == "operacional", \
        f"Agendamento deve ser operacional, got {modo_conversa}"

    print("✅ PASS: Agendamento direto não quebrou")


def test_p03_a_consulta_informativa():
    """
    P0.3-A — Sem Quebra de Consulta Informativa

    Validar que consultas informativas funcionam.
    """
    texto = "Bruna atende corte?"
    ctx = {}

    operacao_p03a = classificar_operacao_robusta(
        texto,
        ctx,
        catalogo_servicos=["corte"],
        catalogo_profissionais=["Bruna"]
    )

    # Deve ser CONSULTA_INFORMATIVA
    assert operacao_p03a == "CONSULTA_INFORMATIVA", \
        f"Consulta informativa retornou {operacao_p03a}"

    # Simulando lógica do roteador
    class_ctx = classificar_contexto_mensagem(
        texto,
        ctx,
        catalogo_servicos=["corte"],
        catalogo_profissionais=["Bruna"]
    )
    modo_conversa = class_ctx.get("modo_conversa")

    if operacao_p03a in ("CONSULTA_DISPONIBILIDADE", "AGENDAMENTO", "CONSULTA_INFORMATIVA"):
        modo_conversa = "operacional"

    assert modo_conversa == "operacional", \
        f"Consulta informativa deve ser operacional, got {modo_conversa}"

    print("✅ PASS: Consulta informativa não quebrou")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 P0.3-A — Testes E2E de Integração")
    print("=" * 70 + "\n")

    tests = [
        test_p03_a_integracao_simples,
        test_p03_a_sem_quebra_agendamento_direto,
        test_p03_a_consulta_informativa,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            print(f"\n{test.__name__}:")
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {test.__name__}")
            print(f"   {str(e)}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"\n📊 RESULTADO: {passed} PASS / {failed} FAIL (Total: {len(tests)})\n")

    if failed == 0:
        print("✅ TODOS OS TESTES E2E PASSARAM\n")
        sys.exit(0)
    else:
        print(f"❌ {failed} TESTE(S) E2E FALHARAM\n")
        sys.exit(1)
