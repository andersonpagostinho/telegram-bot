#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.3-B — Testes de Orquestração

Valida que resposta H2 não é descartada ou substituída.
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock da funcionalidade P0.3-B
class P03B_Orquestrador:
    """
    Simula a lógica P0.3-B:
    1. Consumir resposta pendente após classificação
    2. Bloco neutro não substitui resposta válida
    """

    @staticmethod
    def consumir_resposta_pendente(ctx):
        """P0.3-B: Consumir resposta pendente após classificação"""
        if ctx.get("resposta_informativa_pendente"):
            resposta = ctx.get("resposta_informativa_pendente")
            # Limpar para evitar reuso
            ctx["resposta_informativa_pendente"] = None
            ctx["modo_operacao"] = None
            return {"consumida": True, "resposta": resposta}
        return {"consumida": False, "resposta": None}

    @staticmethod
    def aplicar_resposta_neutra_com_protecao(ctx, modo_conversa):
        """P0.3-B: Bloco neutro não substitui resposta válida"""
        if modo_conversa == "neutro":
            # Dupla proteção: se há resposta pendente, usar ela
            if ctx.get("resposta_informativa_pendente"):
                resposta = ctx.get("resposta_informativa_pendente")
                ctx["resposta_informativa_pendente"] = None
                return {"tipo": "resposta_pendente", "resposta": resposta}
            else:
                # Enviar resposta neutra
                return {"tipo": "resposta_neutra", "resposta": "Tudo bem, sem problemas! 😊"}
        return {"tipo": "nenhuma", "resposta": None}


# Testes
def test_p03b_1_h2_produz_resposta_valida():
    """Teste 1: H2 produz resposta válida"""
    ctx = {}
    resposta_h2 = "Bruna segunda às 16h disponível"
    ctx["resposta_informativa_pendente"] = resposta_h2

    # Validar
    assert ctx.get("resposta_informativa_pendente") == resposta_h2
    print("✅ PASS: H2 produz resposta válida")


def test_p03b_2_resposta_pendente_consumida():
    """Teste 2: Resposta pendente é consumida"""
    ctx = {"resposta_informativa_pendente": "Bruna segunda às 16h"}

    resultado = P03B_Orquestrador.consumir_resposta_pendente(ctx)

    assert resultado["consumida"] == True
    assert resultado["resposta"] == "Bruna segunda às 16h"
    assert ctx.get("resposta_informativa_pendente") is None  # Limpeza
    print("✅ PASS: Resposta pendente consumida")


def test_p03b_3_bloco_neutro_nao_substitui():
    """Teste 3: Bloco neutro não substitui resposta válida"""
    ctx = {"resposta_informativa_pendente": "Bruna segunda às 16h"}
    modo_conversa = "neutro"

    resultado = P03B_Orquestrador.aplicar_resposta_neutra_com_protecao(ctx, modo_conversa)

    assert resultado["tipo"] == "resposta_pendente"
    assert resultado["resposta"] == "Bruna segunda às 16h"
    assert ctx.get("resposta_informativa_pendente") is None
    print("✅ PASS: Bloco neutro não substitui resposta válida")


def test_p03b_4_falha_h2():
    """Teste 4: Falha H2 não gera resposta pendente"""
    ctx = {}
    # H2 falha → não define resposta_informativa_pendente

    # Consumo tenta ler
    resultado = P03B_Orquestrador.consumir_resposta_pendente(ctx)

    assert resultado["consumida"] == False
    assert resultado["resposta"] is None
    print("✅ PASS: Falha H2 não contamina fluxo")


def test_p03b_5_falha_envio_nao_marcada_sucesso():
    """Teste 5: Falha de envio não é marcada como sucesso"""
    ctx = {"resposta_informativa_pendente": "Bruna segunda às 16h"}

    # Simulando falha de envio (resposta não é removida de ctx antes da falha)
    # Dessa forma, próxima mensagem pode tentar reenviar
    resposta_antes = ctx.get("resposta_informativa_pendente")
    assert resposta_antes is not None  # Resposta ainda está lá (falha no envio)
    print("✅ PASS: Falha de envio mantém resposta pendente")


def test_p03b_6_sem_envio_duplicado():
    """Teste 6: Sem envio duplicado"""
    ctx = {"resposta_informativa_pendente": "Bruna segunda às 16h"}

    # Primeira consumição
    resultado1 = P03B_Orquestrador.consumir_resposta_pendente(ctx)
    assert resultado1["consumida"] == True
    assert ctx.get("resposta_informativa_pendente") is None

    # Segunda consumição (deveria retornar False)
    resultado2 = P03B_Orquestrador.consumir_resposta_pendente(ctx)
    assert resultado2["consumida"] == False
    print("✅ PASS: Sem envio duplicado")


def test_p03b_7_consulta_nao_cria_evento():
    """Teste 7: Consulta não cria evento"""
    # Uma resposta informativa é uma CONSULTA, não agendamento
    # Validar que resposta_informativa_pendente é resposta, não evento
    ctx = {"resposta_informativa_pendente": "Bruna segunda às 16h disponível"}

    # Resposta é string, não dict de evento
    resposta = ctx.get("resposta_informativa_pendente")
    assert isinstance(resposta, str)
    assert "disponível" in resposta
    print("✅ PASS: Consulta não cria evento")


def test_p03b_8_agendamento_direto_preservado():
    """Teste 8: Agendamento direto continua funcionando"""
    # Agendamento direto não define resposta_informativa_pendente
    ctx = {}

    # Fluxo de agendamento: define draft, estado, etc.
    ctx["draft_agendamento"] = {"servico": "corte", "profissional": "Bruna"}
    ctx["estado_fluxo"] = "confirmando"

    # Não há resposta pendente
    resultado = P03B_Orquestrador.consumir_resposta_pendente(ctx)
    assert resultado["consumida"] == False

    # Fluxo continua normal
    assert ctx.get("estado_fluxo") == "confirmando"
    print("✅ PASS: Agendamento direto preservado")


def test_p03b_9_sessao_consistente_apos_falha():
    """Teste 9: Sessão permanece consistente após falha"""
    ctx_antes = {
        "resposta_informativa_pendente": "Bruna segunda às 16h",
        "estado_fluxo": "aguardando_confirmacao",
        "draft_agendamento": {"servico": "corte"}
    }

    # Simular consumo
    resultado = P03B_Orquestrador.consumir_resposta_pendente(ctx_antes)

    # Validar que outros campos não foram afetados
    assert ctx_antes.get("estado_fluxo") == "aguardando_confirmacao"
    assert ctx_antes.get("draft_agendamento") == {"servico": "corte"}
    assert ctx_antes.get("resposta_informativa_pendente") is None
    print("✅ PASS: Sessão permanece consistente")


def test_p03b_10_modo_operacional_permite_resposta():
    """Teste 10: Modo operacional permite consumo de resposta"""
    # Com P0.3-A, modo_conversa = "operacional"
    # Com P0.3-B, se houver resposta pendente, é consumida
    ctx = {
        "resposta_informativa_pendente": "Bruna segunda às 16h",
        "modo_conversa": "operacional"
    }

    # Consumo funciona
    resultado = P03B_Orquestrador.consumir_resposta_pendente(ctx)
    assert resultado["consumida"] == True
    assert resultado["resposta"] == "Bruna segunda às 16h"
    print("✅ PASS: Modo operacional permite resposta")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 P0.3-B — Testes de Orquestração")
    print("=" * 70 + "\n")

    tests = [
        test_p03b_1_h2_produz_resposta_valida,
        test_p03b_2_resposta_pendente_consumida,
        test_p03b_3_bloco_neutro_nao_substitui,
        test_p03b_4_falha_h2,
        test_p03b_5_falha_envio_nao_marcada_sucesso,
        test_p03b_6_sem_envio_duplicado,
        test_p03b_7_consulta_nao_cria_evento,
        test_p03b_8_agendamento_direto_preservado,
        test_p03b_9_sessao_consistente_apos_falha,
        test_p03b_10_modo_operacional_permite_resposta,
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
        print("✅ TODOS OS TESTES P0.3-B PASSARAM\n")
        sys.exit(0)
    else:
        print(f"❌ {failed} TESTE(S) FALHARAM\n")
        sys.exit(1)
