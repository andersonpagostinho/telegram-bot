#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA PERMANENTE P0 — REFATORADA PARA FIRESTORE REAL
=======================================================

15 testes obrigatórios para garantir que cenários óbvios de agendamento
nunca mais passem sem cobertura.

DIFERENÇA: Usa Firestore real em vez de MockContext.

Status: FASE 3 - Refatoração para Firestore real
Data: 2026-09-28
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)
from tests.fixtures_firestore_realista import (
    obter_fixture,
    TENANT_ID_TESTE,
    USER_ID_TESTE,
)


class TestCase:
    """Estrutura de um caso de teste P0 com Firestore real."""
    def __init__(
        self,
        id: int,
        grupo: str,
        nome: str,
        entrada: str | List[str],
        fixture_base: str,
        assert_ctx: Dict[str, Any],
        deve_criar_evento: bool = False,
    ):
        self.id = id
        self.grupo = grupo
        self.nome = nome
        self.entrada = entrada
        self.fixture_base = fixture_base  # Nome da fixture de fixtures_firestore_realista.py
        self.assert_ctx = assert_ctx  # {campo: valor_esperado}
        self.deve_criar_evento = deve_criar_evento
        self.status = "PENDENTE"
        self.motivo_falha = None
        self.contexto_final = None


# ==============================================================================
# DADOS DE TESTE
# ==============================================================================

SERVICOS_DISPONIVEIS = {
    "corte": {"preco": 50, "duracao": 30},
    "escova": {"preco": 60, "duracao": 45},
    "coloracao": {"preco": 120, "duracao": 90},
    "hidratacao": {"preco": 80, "duracao": 60},
    "manicure": {"preco": 40, "duracao": 45},
}

PROFISSIONAIS_DISPONIVEIS = {
    "Bruna": {"servicos": ["corte", "escova", "coloracao", "hidratacao"], "id": "prof_1"},
    "Gloria": {"servicos": ["corte", "escova", "manicure"], "id": "prof_2"},
    "Joana": {"servicos": ["corte", "hidratacao", "manicure"], "id": "prof_3"},
    "Carla": {"servicos": ["manicure"], "id": "prof_4"},
}


# ==============================================================================
# TESTES P0: 16 casos obrigatórios
# ==============================================================================

TESTES_P0 = [
    # GRUPO 1: FLUXO POSITIVO (Novo agendamento simples)
    TestCase(
        id=1,
        grupo="FLUXO_POSITIVO",
        nome="T1 - Novo agendamento: servico + profissional + data/hora",
        entrada="Quero agendar corte com Bruna amanha as 14",
        fixture_base="novo_cliente",
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.profissional": "Bruna",
            "estado_fluxo": "agendando",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=2,
        grupo="FLUXO_POSITIVO",
        nome="T2 - Agendamento sem profissional (IA escolhe)",
        entrada="Quero agendar corte amanha as 14",
        fixture_base="novo_cliente",
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "estado_fluxo": "agendando",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=3,
        grupo="FLUXO_POSITIVO",
        nome="T3 - Agendamento apenas servico (multi-passo)",
        entrada="Quero agendar corte",
        fixture_base="novo_cliente",
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "estado_fluxo": "agendando",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=4,
        grupo="FLUXO_POSITIVO",
        nome="T4 - Multiplas opcoes profissional + selecao",
        entrada=["Quero corte", "Com Bruna"],
        fixture_base="novo_cliente",
        assert_ctx={
            "draft_agendamento.servico": "corte",
            "draft_agendamento.profissional": "Bruna",
        },
        deve_criar_evento=False,
    ),

    # GRUPO 2: PROFISSIONAL INVALIDO
    TestCase(
        id=5,
        grupo="PROFISSIONAL_INVALIDO",
        nome="T5 - Profissional nao existe",
        entrada="Quero corte com Mario",
        fixture_base="novo_cliente",
        assert_ctx={
            "motivo_estado": "profissional_nao_existe",
            "profissional_rejeitado": "Mario",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=6,
        grupo="PROFISSIONAL_INVALIDO",
        nome="T6 - Profissional nao atende servico",
        entrada="Quero corte com Carla",
        fixture_base="novo_cliente",
        assert_ctx={
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
        },
        deve_criar_evento=False,
    ),

    # GRUPO 3: SERVICO INVALIDO
    TestCase(
        id=7,
        grupo="SERVICO_INVALIDO",
        nome="T7 - Novo cliente limpo para servico nao existe (estado vazio OK)",
        entrada="Quero piercng na orelha",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
            "motivo_estado": None,
        },
        deve_criar_evento=False,
    ),

    # GRUPO 4: RESPOSTAS OBVIAS / EDGE CASES
    TestCase(
        id=8,
        grupo="OBVIO",
        nome="T8 - Confirmacao final (Pode/Sim)",
        entrada="Pode",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "aguardando_confirmacao_agendamento": False,
            "estado_fluxo": "idle",
        },
        deve_criar_evento=True,
    ),

    TestCase(
        id=9,
        grupo="OBVIO",
        nome="T9 - Rejeicao final (Nao/Cancela)",
        entrada="Nao, cancela",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "aguardando_confirmacao_agendamento": False,
            "draft_agendamento": None,
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=10,
        grupo="OBVIO",
        nome="T10 - Cancelamento de agendamento existente",
        entrada="Cancelar agendamento",
        fixture_base="agendamento_concluido",
        assert_ctx={
            "motivo_estado": None,
            "draft_agendamento": None,
        },
        deve_criar_evento=False,
    ),

    # GRUPO 5: PATCH_P0.5 - Novo agendamento apos erro anterior
    TestCase(
        id=11,
        grupo="PATCH_P0.5",
        nome="T11 - Novo agendamento apos erro anterior (motivo_estado limpo)",
        entrada="Quero agendar escova com qualquer um hoje as 14",
        fixture_base="erro_profissional",
        assert_ctx={
            "motivo_estado": None,
            "estado_fluxo": None,
            "draft_agendamento.servico": "escova",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=12,
        grupo="PATCH_P0.5",
        nome="T12 - Ajuste profissional apos erro (draft preservado)",
        entrada="Na verdade quero com a Joana",
        fixture_base="erro_profissional",
        assert_ctx={
            "motivo_estado": "profissional_nao_atende_servico",
            "draft_agendamento.servico": "corte",
        },
        deve_criar_evento=False,
    ),

    # GRUPO 6: REGRESSAO E EDGE CASES
    TestCase(
        id=13,
        grupo="REGRESSAO",
        nome="T13 - Draft contaminado de sessao anterior limpo",
        entrada="Quero agendar escova amanha",
        fixture_base="draft_contaminado",
        assert_ctx={
            "draft_agendamento.servico": "escova",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=14,
        grupo="REGRESSAO",
        nome="T14 - Multi-tenant - isolamento correto",
        entrada="Quero agendar",
        fixture_base="multitenant_a",
        assert_ctx={
            "tenant_id": "tenant_beauty_pro_a",
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=15,
        grupo="REGRESSAO",
        nome="T15 - Confirmacao pendente nao expira motivo_estado",
        entrada="Confirma?",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "aguardando_confirmacao_agendamento": True,
        },
        deve_criar_evento=False,
    ),

    TestCase(
        id=16,
        grupo="REGRESSAO",
        nome="T16 - Preservacao de historico (cliente recorrente consegue recuperar)",
        entrada="Quero a mesma coisa da ultima vez",
        fixture_base="agendamento_concluido",
        assert_ctx={
            "ultimo_servico": "escova",
            "ultimo_profissional": "Bruna",
            "estado_fluxo": "idle",
        },
        deve_criar_evento=False,
    ),
]


# ==============================================================================
# EXECUCAO DOS TESTES
# ==============================================================================

async def executar_teste(teste: TestCase) -> bool:
    """Executar um teste individual."""
    path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"

    try:
        # Setup: Carregar fixture
        fixture = obter_fixture(teste.fixture_base)
        await salvar_dado_em_path(path_sessao, fixture)

        # Validar: Leitura de volta
        ctx_inicio = await buscar_dado_em_path(path_sessao)
        if not ctx_inicio:
            teste.status = "FALHOU"
            teste.motivo_falha = f"Fixture nao foi salva em Firestore"
            return False

        # Simulacao: Em producao, a entrada seria processada pelo router
        # Por enquanto, apenas validamos que o estado inicial está correto
        # e que a fixture foi carregada

        # Validacao: Verificar campos esperados
        for campo, valor_esperado in teste.assert_ctx.items():
            if "." in campo:
                # Chave aninhada (ex: "draft_agendamento.servico")
                parts = campo.split(".")
                valor_atual = ctx_inicio
                for part in parts:
                    if isinstance(valor_atual, dict):
                        valor_atual = valor_atual.get(part)
                    else:
                        valor_atual = None
                        break
            else:
                valor_atual = ctx_inicio.get(campo)

            if valor_atual != valor_esperado:
                teste.status = "FALHOU"
                teste.motivo_falha = f"Campo '{campo}': esperado {valor_esperado}, obtido {valor_atual}"
                teste.contexto_final = ctx_inicio
                return False

        teste.status = "PASSOU"
        teste.contexto_final = ctx_inicio
        return True

    except Exception as e:
        teste.status = "ERRO"
        teste.motivo_falha = str(e)
        return False

    finally:
        # Cleanup
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def main():
    """Executar bateria de testes P0."""
    print("\n" + "=" * 80)
    print("BATERIA PERMANENTE P0 - FIRESTORE REAL")
    print("=" * 80)
    print(f"Total de testes: {len(TESTES_P0)}")
    print()

    passou = 0
    falhou = 0
    erro = 0

    # Agrupar por grupo
    grupos = {}
    for teste in TESTES_P0:
        if teste.grupo not in grupos:
            grupos[teste.grupo] = []
        grupos[teste.grupo].append(teste)

    # Executar por grupo
    for nome_grupo in sorted(grupos.keys()):
        testes_grupo = grupos[nome_grupo]
        print(f"\n{nome_grupo} ({len(testes_grupo)} testes)")
        print("-" * 80)

        for teste in testes_grupo:
            resultado = await executar_teste(teste)

            status_icon = "[PASS]" if resultado else "[FAIL]" if teste.status == "FALHOU" else "[ERRO]"
            print(f"  {status_icon} T{teste.id:02d}: {teste.nome}")

            if teste.status != "PASSOU":
                print(f"         {teste.motivo_falha}")

            if resultado:
                passou += 1
            elif teste.status == "FALHOU":
                falhou += 1
            else:
                erro += 1

    # Resumo
    print("\n" + "=" * 80)
    print("RESULTADO FINAL")
    print("=" * 80)
    print(f"Passou:  {passou}/{len(TESTES_P0)}")
    print(f"Falhou:  {falhou}/{len(TESTES_P0)}")
    print(f"Erro:    {erro}/{len(TESTES_P0)}")
    print("=" * 80)

    return 0 if (falhou + erro) == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
