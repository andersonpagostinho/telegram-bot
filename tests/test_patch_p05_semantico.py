#!/usr/bin/env python3
"""
Testes obrigatorios para PATCH_P0.5 semantico
T1-T6 conforme aprovado
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.classificador_conversa import classificar_intencao_conversacional


SETUP_CONTEXTO_ERRO = {
    "motivo_estado": "profissional_nao_atende_servico",
    "estado_fluxo": "aguardando_profissional",
    "profissional_rejeitado": "Bruna",
    "profissionais_validos": ["Carla", "Ana", "Zuleica"],
    "draft_agendamento": {
        "servico": "corte",
        "data_hora": "2026-09-28T17:00:00"
    }
}


def classificar_com_logica(entrada, ctx):
    """Replicar logica do router: limpar estado_fluxo se há motivo_estado erro"""
    ctx_para_classificacao = ctx.copy()
    if ctx_para_classificacao.get("motivo_estado") == "profissional_nao_atende_servico":
        ctx_para_classificacao.pop("estado_fluxo", None)
    return classificar_intencao_conversacional(entrada, ctx_para_classificacao)


def test_t1_novo_agendamento():
    """T1: Novo agendamento direto"""
    entrada = "quero agendar escova hoje às 14"
    ctx = SETUP_CONTEXTO_ERRO.copy()

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "agendamento_direto", \
        f"T1: Esperado agendamento_direto, obtido {class_intencao.get('intencao_conversacional')}"
    assert class_intencao.get("confianca") >= 85, \
        f"T1: Confianca esperada >= 85, obtida {class_intencao.get('confianca')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("motivo_estado", None)
        ctx.pop("estado_fluxo", None)
        ctx.pop("profissional_rejeitado", None)
        ctx.pop("profissionais_validos", None)
        ctx.pop("draft_agendamento", None)
        ctx.pop("profissional_escolhido", None)

    assert ctx.get("motivo_estado") is None, "T1: motivo_estado deveria estar None"
    assert ctx.get("estado_fluxo") is None, "T1: estado_fluxo deveria estar None"
    assert ctx.get("draft_agendamento") is None, "T1: draft_agendamento deveria estar None"

    print("[PASS] T1: Novo agendamento processado corretamente")
    return True


def test_t2_ajuste_profissional():
    """T2: Ajuste de profissional (risco principal)"""
    entrada = "Na verdade quero com a Carla"
    ctx = SETUP_CONTEXTO_ERRO.copy()
    ctx["draft_agendamento"] = {
        "servico": "corte",
        "data_hora": "2026-09-28T17:00:00"
    }

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "ajuste_incremental", \
        f"T2: Esperado ajuste_incremental, obtido {class_intencao.get('intencao_conversacional')}"
    assert class_intencao.get("tipo_ajuste_incremental") == "profissional", \
        f"T2: Tipo esperado profissional, obtido {class_intencao.get('tipo_ajuste_incremental')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("draft_agendamento", None)

    assert ctx.get("draft_agendamento") is not None, "T2: draft deveria ser preservado!"
    assert ctx.get("draft_agendamento").get("servico") == "corte", "T2: servico deveria estar preservado"

    print("[PASS] T2: Ajuste profissional sem destruir draft")
    return True


def test_t3_ajuste_horario():
    """T3: Ajuste de horario"""
    entrada = "quero outro horario"
    ctx = SETUP_CONTEXTO_ERRO.copy()
    ctx["draft_agendamento"] = {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-09-28T17:00:00"
    }

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "ajuste_incremental", \
        f"T3: Esperado ajuste_incremental, obtido {class_intencao.get('intencao_conversacional')}"
    assert class_intencao.get("tipo_ajuste_incremental") == "horario", \
        f"T3: Tipo esperado horario, obtido {class_intencao.get('tipo_ajuste_incremental')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("draft_agendamento", None)

    assert ctx.get("draft_agendamento") is not None, "T3: draft deveria ser preservado!"

    print("[PASS] T3: Ajuste horario sem destruir draft")
    return True


def test_t4_ajuste_servico():
    """T4: Ajuste de servico"""
    entrada = "na verdade prefiro coloracao"
    ctx = SETUP_CONTEXTO_ERRO.copy()
    ctx["draft_agendamento"] = {
        "servico": "corte",
        "profissional": "Bruna",
        "data_hora": "2026-09-28T17:00:00"
    }

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "ajuste_incremental", \
        f"T4: Esperado ajuste_incremental, obtido {class_intencao.get('intencao_conversacional')}"
    assert class_intencao.get("tipo_ajuste_incremental") == "servico", \
        f"T4: Tipo esperado servico, obtido {class_intencao.get('tipo_ajuste_incremental')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("draft_agendamento", None)

    assert ctx.get("draft_agendamento") is not None, "T4: draft deveria ser preservado!"

    print("[PASS] T4: Ajuste servico sem destruir draft")
    return True


def test_t5_indefinida():
    """T5: Intencao indefinida"""
    entrada = "texto aleatorio"
    ctx = SETUP_CONTEXTO_ERRO.copy()

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "indefinida", \
        f"T5: Esperado indefinida, obtido {class_intencao.get('intencao_conversacional')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("draft_agendamento", None)

    assert ctx.get("draft_agendamento") is not None, "T5: draft deveria ser preservado!"

    print("[PASS] T5: Intencao indefinida sem destruir draft")
    return True


def test_t6_cancelamento():
    """T6: Cancelamento"""
    entrada = "cancela"
    ctx = SETUP_CONTEXTO_ERRO.copy()

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "cancelamento", \
        f"T6: Esperado cancelamento, obtido {class_intencao.get('intencao_conversacional')}"

    print("[PASS] T6: Cancelamento classificado corretamente")
    return True


def test_pedido_aberto_temporal():
    """Teste extra: pedido_aberto_temporal tambem deve resetar"""
    entrada = "desejo marcar amanha"
    ctx = SETUP_CONTEXTO_ERRO.copy()

    class_intencao = classificar_com_logica(entrada, ctx)

    assert class_intencao.get("intencao_conversacional") == "pedido_aberto_temporal", \
        f"Teste extra: Esperado pedido_aberto_temporal, obtido {class_intencao.get('intencao_conversacional')}"

    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("draft_agendamento", None)

    assert ctx.get("draft_agendamento") is None, "Teste extra: draft deveria estar None"

    print("[PASS] Teste extra: pedido_aberto_temporal resetou draft")
    return True


def main():
    print("=" * 70)
    print("TESTES OBRIGATORIOS: PATCH_P0.5 SEMANTICO")
    print("=" * 70)
    print()

    testes = [
        ("T1 -- Novo agendamento", test_t1_novo_agendamento),
        ("T2 -- Ajuste profissional", test_t2_ajuste_profissional),
        ("T3 -- Ajuste horario", test_t3_ajuste_horario),
        ("T4 -- Ajuste servico", test_t4_ajuste_servico),
        ("T5 -- Intencao indefinida", test_t5_indefinida),
        ("T6 -- Cancelamento", test_t6_cancelamento),
        ("Extra -- pedido_aberto_temporal", test_pedido_aberto_temporal),
    ]

    passou = 0
    falhou = 0

    for nome, teste_func in testes:
        try:
            teste_func()
            passou += 1
        except AssertionError as e:
            print(f"[FAIL] {nome}: {e}")
            falhou += 1
        except Exception as e:
            print(f"[ERROR] {nome}: {e}")
            falhou += 1

    print()
    print("=" * 70)
    print(f"RESULTADO: {passou} PASS, {falhou} FAIL")
    print("=" * 70)

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
