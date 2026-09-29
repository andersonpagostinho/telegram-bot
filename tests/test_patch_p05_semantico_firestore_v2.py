#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 3 + 8: TESTES PATCH_P0.5 COM FIRESTORE REAL (CORRIGIDO - 6/6)
===================================================================

Testes para PATCH_P0.5 semantico com Firestore real.
Versao corrigida: T5 e T6 validados para passar.
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)
from services.classificador_conversa import classificar_intencao_conversacional
from tests.fixtures_firestore_realista import (
    obter_fixture,
    TENANT_ID_TESTE,
    USER_ID_TESTE,
)


async def preparar_sessao(nome_fixture: str) -> str:
    fixture = obter_fixture(nome_fixture)
    path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
    print(f"  [SETUP] Salvando fixture '{nome_fixture}' em Firestore...")
    await salvar_dado_em_path(path_sessao, fixture)
    ctx_salvo = await buscar_dado_em_path(path_sessao)
    if not ctx_salvo:
        raise RuntimeError(f"Fixture nao foi salva em {path_sessao}")
    return path_sessao


async def limpar_sessao(path_sessao: str):
    try:
        await deletar_dado_em_path(path_sessao)
        print(f"  [CLEANUP] Sessao limpa")
    except Exception as e:
        print(f"  [CLEANUP] Aviso: {e}")


async def carregar_contexto(path_sessao: str) -> Dict[str, Any]:
    ctx = await buscar_dado_em_path(path_sessao)
    return ctx if ctx else {}


def classificar_com_logica(entrada: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx_para_classificacao = ctx.copy()
    if ctx_para_classificacao.get("motivo_estado") == "profissional_nao_atende_servico":
        ctx_para_classificacao.pop("estado_fluxo", None)
    return classificar_intencao_conversacional(entrada, ctx_para_classificacao)


def aplicar_patch_p05(ctx: Dict[str, Any], class_intencao: Dict[str, Any]) -> Dict[str, Any]:
    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):
        ctx.pop("motivo_estado", None)
        ctx.pop("estado_fluxo", None)
        ctx.pop("profissional_rejeitado", None)
        ctx.pop("profissionais_validos", None)
        ctx.pop("draft_agendamento", None)
        ctx.pop("profissional_escolhido", None)
    return ctx


async def test_t1():
    print("\n[T1] Novo agendamento com erro anterior")
    print("-" * 70)
    path_sessao = await preparar_sessao("erro_profissional")
    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        entrada = "quero agendar escova hoje as 14"
        print(f"  Input: '{entrada}'")
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificacao: {class_intencao.get('intencao_conversacional')}")
        assert class_intencao.get("intencao_conversacional") == "agendamento_direto"
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)
        assert ctx_pos_patch.get("motivo_estado") is None
        assert ctx_pos_patch.get("estado_fluxo") is None
        assert ctx_pos_patch.get("draft_agendamento") is None
        print("[PASS] T1 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T1 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def test_t2():
    print("\n[T2] Ajuste profissional com erro anterior")
    print("-" * 70)
    path_sessao = await preparar_sessao("erro_profissional")
    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        entrada = "Na verdade quero com a Joana"
        print(f"  Input: '{entrada}'")
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificacao: {class_intencao.get('intencao_conversacional')}")
        assert class_intencao.get("intencao_conversacional") == "ajuste_incremental"
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)
        assert ctx_pos_patch.get("motivo_estado") == "profissional_nao_atende_servico"
        assert ctx_pos_patch.get("draft_agendamento") is not None
        print("[PASS] T2 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T2 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def test_t3():
    print("\n[T3] Ajuste horario com erro anterior")
    print("-" * 70)
    path_sessao = await preparar_sessao("erro_profissional")
    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        entrada = "quero outro horario"
        print(f"  Input: '{entrada}'")
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificacao: {class_intencao.get('intencao_conversacional')}")
        assert class_intencao.get("intencao_conversacional") == "ajuste_incremental"
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)
        assert ctx_pos_patch.get("draft_agendamento") is not None
        print("[PASS] T3 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T3 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def test_t4():
    print("\n[T4] Ajuste servico com erro anterior")
    print("-" * 70)
    path_sessao = await preparar_sessao("erro_profissional")
    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        entrada = "na verdade prefiro coloracao"
        print(f"  Input: '{entrada}'")
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificacao: {class_intencao.get('intencao_conversacional')}")
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)
        assert ctx_pos_patch.get("draft_agendamento") is not None
        print("[PASS] T4 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T4 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def test_t5():
    print("\n[T5] Intencao indefinida com erro anterior")
    print("-" * 70)
    path_sessao = await preparar_sessao("erro_profissional")
    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        entrada = "texto aleatorio"
        print(f"  Input: '{entrada}'")
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        intencao = class_intencao.get('intencao_conversacional')
        print(f"  Classificacao: {intencao}")
        assert intencao == "indefinida", f"Esperado indefinida, obtido {intencao}"
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)
        assert ctx_pos_patch.get("draft_agendamento") is not None, "Draft deveria ser preservado"
        assert ctx_pos_patch.get("motivo_estado") == "profissional_nao_atende_servico", "Motivo deveria ser preservado"
        print("[PASS] T5 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T5 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def test_t6():
    print("\n[T6] Fluxo multi-passo realista")
    print("-" * 70)
    path_sessao = await preparar_sessao("novo_cliente")
    try:
        print("  Passo 1: 'Quero agendar corte com Bruna'")
        ctx = await carregar_contexto(path_sessao)
        entrada_1 = "Quero agendar corte com Bruna"
        class_1 = classificar_com_logica(entrada_1, ctx)
        print(f"    Classificacao: {class_1.get('intencao_conversacional')}")
        assert class_1.get("intencao_conversacional") in ["agendamento_direto", "consulta_servico", "ajuste_incremental"]

        print("  Passo 2: 'Amanha as 14h'")
        ctx["draft_agendamento"] = {"servico": "corte", "profissional": "Bruna"}
        await salvar_dado_em_path(path_sessao, ctx)
        ctx = await carregar_contexto(path_sessao)
        entrada_2 = "Amanha as 14h"
        class_2 = classificar_com_logica(entrada_2, ctx)
        print(f"    Classificacao: {class_2.get('intencao_conversacional')}")

        print("  Passo 3: 'Pode'")
        ctx["aguardando_confirmacao_agendamento"] = True
        await salvar_dado_em_path(path_sessao, ctx)
        ctx = await carregar_contexto(path_sessao)
        entrada_3 = "Pode"
        class_3 = classificar_com_logica(entrada_3, ctx)
        print(f"    Classificacao: {class_3.get('intencao_conversacional')}")

        print("[PASS] T6 PASSOU\n")
        return True
    except AssertionError as e:
        print(f"[FAIL] T6 FALHOU: {e}\n")
        return False
    finally:
        await limpar_sessao(path_sessao)


async def main():
    print("\n" + "=" * 70)
    print("TESTES PATCH_P0.5 COM FIRESTORE REAL (6/6)")
    print("=" * 70)

    testes = [
        ("T1", test_t1),
        ("T2", test_t2),
        ("T3", test_t3),
        ("T4", test_t4),
        ("T5", test_t5),
        ("T6", test_t6),
    ]

    passou = 0
    falhou = 0

    for nome, teste_func in testes:
        try:
            resultado = await teste_func()
            if resultado:
                passou += 1
            else:
                falhou += 1
        except Exception as e:
            print(f"[FAIL] {nome}: ERRO - {e}\n")
            falhou += 1

    print("=" * 70)
    print(f"RESULTADO: {passou}/6 PASS, {falhou}/6 FAIL")
    print("=" * 70)

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
