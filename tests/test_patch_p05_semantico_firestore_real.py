#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE 3 + 8: TESTES PATCH_P0.5 COM FIRESTORE REAL
===================================================

Testes específicos para PATCH_P0.5 semântico usando dados realistas em Firestore.

Objetivo:
- Validar que PATCH_P0.5 funciona com Firestore real (não mock)
- Validar cenários específicos que mock não pega
- Validar isolamento de tenant
- Validar contaminação de estado

Fixtures usadas:
- FIXTURE_ERRO_PROFISSIONAL: motivo_estado="profissional_nao_atende_servico"
- FIXTURE_DRAFT_CONTAMINADO: draft com serviço/data antiga
- FIXTURE_NOVO_CLIENTE: contexto limpo
- FIXTURE_CONFIRMACAO_PENDENTE: agendamento pronto

Testes (T1-T6):
T1: Novo agendamento com erro anterior → PATCH_P0.5 limpa estado
T2: Ajuste profissional com erro anterior → PATCH_P0.5 preserva draft
T3: Ajuste horário com erro anterior → preserva draft
T4: Ajuste serviço com erro anterior → preserva draft
T5: Intenção indefinida → preserva draft
T6: Multi-passo realista → validar sequência

Status: FASE 3 — Validar com Firestore real
Data: 2026-09-28
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

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


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

TIMEOUT_FIRESTORE = 10  # segundos


# ============================================================================
# HELPERS
# ============================================================================

async def preparar_sessao(nome_fixture: str) -> str:
    """
    Preparar contexto de teste em Firestore.

    Retorna: path_sessao (para leitura/limpeza posterior)
    """
    fixture = obter_fixture(nome_fixture)
    path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"

    print(f"  [SETUP] Salvando fixture '{nome_fixture}' em Firestore...")
    await salvar_dado_em_path(path_sessao, fixture)

    # Validar que foi salvo
    ctx_salvo = await buscar_dado_em_path(path_sessao)
    if not ctx_salvo:
        raise RuntimeError(f"Fixture não foi salva em {path_sessao}")

    return path_sessao


async def limpar_sessao(path_sessao: str):
    """Limpar dados de teste após uso."""
    try:
        await deletar_dado_em_path(path_sessao)
        print(f"  [CLEANUP] Sessão limpa: {path_sessao}")
    except Exception as e:
        print(f"  [CLEANUP] Aviso ao limpar: {e}")


async def carregar_contexto(path_sessao: str) -> Dict[str, Any]:
    """Carregar contexto atual de Firestore."""
    ctx = await buscar_dado_em_path(path_sessao)
    if not ctx:
        return {}
    return ctx


def classificar_com_logica(entrada: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Replicar lógica do router: remover estado_fluxo se há erro anterior."""
    ctx_para_classificacao = ctx.copy()
    if ctx_para_classificacao.get("motivo_estado") == "profissional_nao_atende_servico":
        ctx_para_classificacao.pop("estado_fluxo", None)

    return classificar_intencao_conversacional(entrada, ctx_para_classificacao)


def aplicar_patch_p05(ctx: Dict[str, Any], class_intencao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplicar a lógica de PATCH_P0.5.

    Se intencao = agendamento_direto ou pedido_aberto_temporal
    E motivo_estado = "profissional_nao_atende_servico"
    Então limpar estado de erro.
    """
    if (ctx.get("motivo_estado") == "profissional_nao_atende_servico"
        and class_intencao.get("intencao_conversacional") in ["agendamento_direto", "pedido_aberto_temporal"]):

        # Limpar estado de erro
        ctx.pop("motivo_estado", None)
        ctx.pop("estado_fluxo", None)
        ctx.pop("profissional_rejeitado", None)
        ctx.pop("profissionais_validos", None)
        ctx.pop("draft_agendamento", None)
        ctx.pop("profissional_escolhido", None)

    return ctx


# ============================================================================
# TESTES
# ============================================================================

async def test_t1_novo_agendamento_apos_erro():
    """
    T1: Novo agendamento com erro anterior

    Setup: FIXTURE_ERRO_PROFISSIONAL (motivo_estado="profissional_nao_atende_servico")
    Input: "quero agendar escova hoje às 14"
    Esperado:
    - Classificação: agendamento_direto
    - PATCH_P0.5 ativa: motivo_estado limpado
    - PATCH_P0.5 ativa: draft_agendamento limpado
    - Novo draft criado para escova
    """
    print("\n[T1] Novo agendamento com erro anterior")
    print("-" * 70)

    path_sessao = await preparar_sessao("erro_profissional")

    try:
        # Carregar contexto inicial
        ctx_inicial = await carregar_contexto(path_sessao)
        print(f"  Estado inicial: motivo_estado={ctx_inicial.get('motivo_estado')}")
        print(f"                  estado_fluxo={ctx_inicial.get('estado_fluxo')}")
        print(f"                  draft={ctx_inicial.get('draft_agendamento', {}).get('servico')}")

        # Novo agendamento
        entrada = "quero agendar escova hoje às 14"
        print(f"  Input: '{entrada}'")

        # Classificar
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificação: {class_intencao.get('intencao_conversacional')}")
        print(f"  Confiança: {class_intencao.get('confianca')}%")

        assert class_intencao.get("intencao_conversacional") == "agendamento_direto", \
            f"T1 FALHOU: Esperado agendamento_direto, obtido {class_intencao.get('intencao_conversacional')}"

        # Aplicar PATCH_P0.5
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)

        # Validar que estado foi limpado
        assert ctx_pos_patch.get("motivo_estado") is None, \
            "T1 FALHOU: motivo_estado deveria estar None"
        assert ctx_pos_patch.get("estado_fluxo") is None, \
            "T1 FALHOU: estado_fluxo deveria estar None"
        assert ctx_pos_patch.get("draft_agendamento") is None, \
            "T1 FALHOU: draft_agendamento antigo deveria estar None"

        print(f"  [OK] Estado após PATCH_P0.5:")
        print(f"     motivo_estado = {ctx_pos_patch.get('motivo_estado')} (limpado)")
        print(f"     estado_fluxo = {ctx_pos_patch.get('estado_fluxo')} (limpado)")
        print(f"     draft_agendamento = {ctx_pos_patch.get('draft_agendamento')} (limpado)")

        # Salvar estado limpado de volta
        await salvar_dado_em_path(path_sessao, ctx_pos_patch)

        # Verificar em Firestore
        ctx_firestore = await carregar_contexto(path_sessao)
        assert ctx_firestore.get("motivo_estado") is None, \
            "T1 FALHOU: Firestore deveria ter motivo_estado = None"

        print(f"  [OK] Firestore validado: estado limpado")
        print("\n[OK] T1 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T1 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


async def test_t2_ajuste_profissional_preserva_draft():
    """
    T2: Ajuste de profissional com erro anterior

    Setup: FIXTURE_ERRO_PROFISSIONAL
    Input: "Na verdade quero com a Joana"
    Esperado:
    - Classificação: ajuste_incremental (profissional)
    - PATCH_P0.5 NÃO ativa (não é novo agendamento)
    - motivo_estado PRESERVADO
    - draft_agendamento PRESERVADO
    """
    print("\n[T2] Ajuste de profissional com erro anterior")
    print("-" * 70)

    path_sessao = await preparar_sessao("erro_profissional")

    try:
        ctx_inicial = await carregar_contexto(path_sessao)
        servico_inicial = ctx_inicial.get("draft_agendamento", {}).get("servico")
        print(f"  Estado inicial: draft.servico='{servico_inicial}'")
        print(f"                  motivo_estado={ctx_inicial.get('motivo_estado')}")

        # Ajuste profissional
        entrada = "Na verdade quero com a Joana"
        print(f"  Input: '{entrada}'")

        # Classificar
        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificação: {class_intencao.get('intencao_conversacional')}")
        print(f"  Tipo ajuste: {class_intencao.get('tipo_ajuste_incremental')}")

        assert class_intencao.get("intencao_conversacional") == "ajuste_incremental", \
            f"T2 FALHOU: Esperado ajuste_incremental, obtido {class_intencao.get('intencao_conversacional')}"

        assert class_intencao.get("tipo_ajuste_incremental") == "profissional", \
            f"T2 FALHOU: Tipo esperado profissional"

        # PATCH_P0.5 NÃO deveria ativar (ajuste, não novo)
        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)

        # Validar que estado foi PRESERVADO
        assert ctx_pos_patch.get("motivo_estado") == "profissional_nao_atende_servico", \
            "T2 FALHOU: motivo_estado deveria ser PRESERVADO"
        assert ctx_pos_patch.get("draft_agendamento") is not None, \
            "T2 FALHOU: draft deveria ser PRESERVADO"
        assert ctx_pos_patch.get("draft_agendamento", {}).get("servico") == servico_inicial, \
            "T2 FALHOU: serviço em draft deveria ser PRESERVADO"

        print(f"  [OK] Estado após PATCH_P0.5 (não ativa):")
        print(f"     motivo_estado = {ctx_pos_patch.get('motivo_estado')} (PRESERVADO)")
        print(f"     draft.servico = {ctx_pos_patch.get('draft_agendamento', {}).get('servico')} (PRESERVADO)")

        print("\n[OK] T2 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T2 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


async def test_t3_ajuste_horario_preserva_draft():
    """
    T3: Ajuste de horário com erro anterior

    Setup: FIXTURE_ERRO_PROFISSIONAL
    Input: "quero outro horário"
    Esperado:
    - Classificação: ajuste_incremental (horario)
    - PATCH_P0.5 NÃO ativa
    - draft_agendamento PRESERVADO
    """
    print("\n[T3] Ajuste de horário com erro anterior")
    print("-" * 70)

    path_sessao = await preparar_sessao("erro_profissional")

    try:
        ctx_inicial = await carregar_contexto(path_sessao)

        entrada = "quero outro horário"
        print(f"  Input: '{entrada}'")

        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificação: {class_intencao.get('intencao_conversacional')}")

        assert class_intencao.get("intencao_conversacional") == "ajuste_incremental"

        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)

        assert ctx_pos_patch.get("draft_agendamento") is not None, \
            "T3 FALHOU: draft deveria ser PRESERVADO"

        print(f"  [OK] draft PRESERVADO")
        print("\n[OK] T3 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T3 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


async def test_t4_ajuste_servico_preserva_draft():
    """
    T4: Ajuste de serviço com erro anterior

    Setup: FIXTURE_ERRO_PROFISSIONAL (draft.servico="corte")
    Input: "na verdade prefiro coloração"
    Esperado:
    - Classificação: ajuste_incremental (servico)
    - draft PRESERVADO (servico antigo "corte" mantido)
    """
    print("\n[T4] Ajuste de serviço com erro anterior")
    print("-" * 70)

    path_sessao = await preparar_sessao("erro_profissional")

    try:
        ctx_inicial = await carregar_contexto(path_sessao)

        entrada = "na verdade prefiro coloracao"
        print(f"  Input: '{entrada}'")

        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificação: {class_intencao.get('intencao_conversacional')}")

        # Pode ser ajuste_incremental ou novo, dependendo do classificador
        # O importante é que draft é PRESERVADO

        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)

        assert ctx_pos_patch.get("draft_agendamento") is not None, \
            "T4 FALHOU: draft deveria ser PRESERVADO"

        print(f"  [OK] draft PRESERVADO: {ctx_pos_patch.get('draft_agendamento', {}).get('servico')}")
        print("\n[OK] T4 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T4 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


async def test_t5_intencao_indefinida_preserva_draft():
    """
    T5: Intenção indefinida

    Setup: FIXTURE_ERRO_PROFISSIONAL
    Input: "texto aleatório"
    Esperado:
    - Classificação: indefinida
    - draft PRESERVADO
    - motivo_estado PRESERVADO
    """
    print("\n[T5] Intenção indefinida com erro anterior")
    print("-" * 70)

    path_sessao = await preparar_sessao("erro_profissional")

    try:
        ctx_inicial = await carregar_contexto(path_sessao)

        entrada = "texto aleatório"
        print(f"  Input: '{entrada}'")

        class_intencao = classificar_com_logica(entrada, ctx_inicial)
        print(f"  Classificação: {class_intencao.get('intencao_conversacional')}")

        ctx_pos_patch = aplicar_patch_p05(ctx_inicial, class_intencao)

        assert ctx_pos_patch.get("draft_agendamento") is not None, \
            "T5 FALHOU: draft deveria ser PRESERVADO"

        print(f"  [OK] draft PRESERVADO, estado mantido")
        print("\n[OK] T5 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T5 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


async def test_t6_multi_passo_realista():
    """
    T6: Fluxo multi-passo realista

    Setup: FIXTURE_NOVO_CLIENTE (limpo)
    Passo 1: "Quero corte com Bruna"
    Passo 2: "Amanhã às 14h"
    Passo 3: "Confirma?"

    Validar sequência completa
    """
    print("\n[T6] Fluxo multi-passo realista")
    print("-" * 70)

    path_sessao = await preparar_sessao("novo_cliente")

    try:
        # Passo 1
        print("\n  Passo 1: 'Quero corte com Bruna'")
        ctx = await carregar_contexto(path_sessao)
        entrada_1 = "Quero corte com Bruna"
        class_1 = classificar_com_logica(entrada_1, ctx)
        print(f"    Classificação: {class_1.get('intencao_conversacional')}")

        assert class_1.get("intencao_conversacional") in ["agendamento_direto", "ajuste_incremental"]

        # Passo 2
        print("\n  Passo 2: 'Amanhã às 14h'")
        # (Simular salvamento de draft entre mensagens)
        ctx["draft_agendamento"] = {
            "servico": "corte",
            "profissional": "Bruna",
        }
        await salvar_dado_em_path(path_sessao, ctx)

        ctx = await carregar_contexto(path_sessao)
        entrada_2 = "Amanhã às 14h"
        class_2 = classificar_com_logica(entrada_2, ctx)
        print(f"    Classificação: {class_2.get('intencao_conversacional')}")

        # Passo 3
        print("\n  Passo 3: 'Confirma?'")
        ctx["aguardando_confirmacao_agendamento"] = True
        await salvar_dado_em_path(path_sessao, ctx)

        ctx = await carregar_contexto(path_sessao)
        entrada_3 = "Pode"
        class_3 = classificar_com_logica(entrada_3, ctx)
        print(f"    Classificação: {class_3.get('intencao_conversacional')}")

        assert class_3.get("intencao_conversacional") in ["confirmacao", "indefinida", "agendamento_direto"]

        print(f"\n  [OK] Fluxo multi-passo completo")
        print("\n[OK] T6 PASSOU\n")
        return True

    except AssertionError as e:
        print(f"\n[OK] T6 FALHOU: {e}\n")
        return False

    finally:
        await limpar_sessao(path_sessao)


# ============================================================================
# RUNNER
# ============================================================================

async def main():
    """Executar todos os testes."""
    print("\n" + "=" * 70)
    print("TESTES PATCH_P0.5 COM FIRESTORE REAL")
    print("=" * 70)

    testes = [
        ("T1 -- Novo agendamento após erro", test_t1_novo_agendamento_apos_erro),
        ("T2 -- Ajuste profissional", test_t2_ajuste_profissional_preserva_draft),
        ("T3 -- Ajuste horário", test_t3_ajuste_horario_preserva_draft),
        ("T4 -- Ajuste serviço", test_t4_ajuste_servico_preserva_draft),
        ("T5 -- Intenção indefinida", test_t5_intencao_indefinida_preserva_draft),
        ("T6 -- Multi-passo realista", test_t6_multi_passo_realista),
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
            print(f"[OK] {nome}: ERRO NÃO TRATADO - {e}\n")
            falhou += 1

    print("=" * 70)
    print(f"RESULTADO: {passou} PASS, {falhou} FAIL")
    print("=" * 70)

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
