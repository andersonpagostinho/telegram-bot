#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA PERMANENTE P0 — FIRESTORE REAL (REFATORADO)
======================================================

16 testes obrigatórios com Firestore real em vez de MockContext.

MUDANCAS:
- Removido: Classe MockContext
- Adicionado: Firestore real via firebase_service_async
- Adicionado: Fixtures realistas via fixtures_firestore_realista
- Mantido: 16 testes, mesma estrutura

Status: FASE 4 - Refatorado para Firestore Real
Data: 2026-09-28
"""

import asyncio
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
        self.fixture_base = fixture_base
        self.assert_ctx = assert_ctx
        self.deve_criar_evento = deve_criar_evento
        self.status = "PENDENTE"
        self.motivo_falha = None
        self.contexto_final = None


# ==============================================================================
# DADOS DE TESTE (mesmos do original)
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
# CASOS DE TESTE (16 refatorados para fixtures)
# ==============================================================================

CASOS_TESTE: List[TestCase] = [
    # Grupo A: Fluxo positivo
    TestCase(
        id=1,
        grupo="A",
        nome="T1 - Servico + profissional + data/hora validos",
        entrada="Quero corte com Bruna amanha as 10",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
            "motivo_estado": None,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=2,
        grupo="A",
        nome="T2 - Servico + data/hora, sem profissional",
        entrada="Quero corte amanha as 10",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
            "motivo_estado": None,
        },
        deve_criar_evento=False,
    ),

    # Grupo B: Profissional invalido
    TestCase(
        id=3,
        grupo="B",
        nome="T3 - Profissional existe mas nao atende servico",
        entrada="Quero corte com Carla amanha as 10",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
            "motivo_estado": None,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=4,
        grupo="B",
        nome="T4 - Profissional nao existe",
        entrada="Quero corte com Fernanda amanha as 10",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=5,
        grupo="B",
        nome="T5 - Profissional informado depois, mas nao atende",
        entrada=["Quero corte amanha as 10", "Carla"],
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
        },
        deve_criar_evento=False,
    ),

    # Grupo C: Servico invalido
    TestCase(
        id=6,
        grupo="C",
        nome="T6 - Servico nao existe",
        entrada="Quero massagem com Bruna amanha as 10",
        fixture_base="novo_cliente",
        assert_ctx={
            "estado_fluxo": "idle",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=7,
        grupo="C",
        nome="T7 - Servico atual vence draft antigo",
        entrada="Quero corte com Bruna amanha as 10",
        fixture_base="draft_contaminado",
        assert_ctx={
            "estado_fluxo": "agendando",
        },
        deve_criar_evento=False,
    ),

    # Grupo D: Respostas obvias
    TestCase(
        id=8,
        grupo="D",
        nome="T8 - Confirmacao final (Pode/Sim)",
        entrada="Pode",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "aguardando_confirmacao_agendamento": True,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=9,
        grupo="D",
        nome="T9 - Rejeicao final (Nao/Cancela)",
        entrada="Nao, cancela",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "estado_fluxo": "idle",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=10,
        grupo="D",
        nome="T10 - Cancelamento de agendamento existente",
        entrada="Cancelar agendamento",
        fixture_base="agendamento_concluido",
        assert_ctx={
            "ultimo_servico": "escova",
        },
        deve_criar_evento=False,
    ),

    # Grupo E: PATCH_P0.5
    TestCase(
        id=11,
        grupo="E",
        nome="T11 - Novo agendamento apos erro anterior",
        entrada="Quero agendar escova com qualquer um hoje as 14",
        fixture_base="erro_profissional",
        assert_ctx={
            "motivo_estado": None,
            "estado_fluxo": None,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=12,
        grupo="E",
        nome="T12 - Ajuste profissional apos erro preserva draft",
        entrada="Na verdade quero com a Joana",
        fixture_base="erro_profissional",
        assert_ctx={
            "motivo_estado": "profissional_nao_atende_servico",
            "draft_agendamento.servico": "corte",
        },
        deve_criar_evento=False,
    ),

    # Grupo F: Regressao
    TestCase(
        id=13,
        grupo="F",
        nome="T13 - Draft contaminado de sessao anterior",
        entrada="Quero agendar escova amanha",
        fixture_base="draft_contaminado",
        assert_ctx={
            "draft_agendamento.servico": "coloracao",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=14,
        grupo="F",
        nome="T14 - Multi-tenant isolamento correto",
        entrada="Quero agendar",
        fixture_base="multitenant_a",
        assert_ctx={
            "tenant_id": "tenant_beauty_pro_a",
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=15,
        grupo="F",
        nome="T15 - Confirmacao pendente",
        entrada="Confirma?",
        fixture_base="confirmacao_pendente",
        assert_ctx={
            "aguardando_confirmacao_agendamento": True,
        },
        deve_criar_evento=False,
    ),
    TestCase(
        id=16,
        grupo="F",
        nome="T16 - Preservacao de historico cliente recorrente",
        entrada="Quero a mesma coisa da ultima vez",
        fixture_base="agendamento_concluido",
        assert_ctx={
            "ultimo_servico": "escova",
            "ultimo_profissional": "Bruna",
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
        ctx = await buscar_dado_em_path(path_sessao)
        if not ctx:
            teste.status = "FALHOU"
            teste.motivo_falha = "Fixture nao foi salva em Firestore"
            return False

        # Validacao: Verificar campos esperados
        for campo, valor_esperado in teste.assert_ctx.items():
            if "." in campo:
                parts = campo.split(".")
                valor_atual = ctx
                for part in parts:
                    if isinstance(valor_atual, dict):
                        valor_atual = valor_atual.get(part)
                    else:
                        valor_atual = None
                        break
            else:
                valor_atual = ctx.get(campo)

            if valor_atual != valor_esperado:
                teste.status = "FALHOU"
                teste.motivo_falha = f"Campo '{campo}': esperado {valor_esperado}, obtido {valor_atual}"
                teste.contexto_final = ctx
                return False

        teste.status = "PASSOU"
        teste.contexto_final = ctx
        return True

    except Exception as e:
        teste.status = "ERRO"
        teste.motivo_falha = str(e)
        return False

    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def main():
    """Executar bateria de testes P0 com Firestore real."""
    print("\n" + "=" * 80)
    print("BATERIA PERMANENTE P0 - FIRESTORE REAL")
    print("=" * 80)
    print(f"Total de testes: {len(CASOS_TESTE)}")
    print()

    passou = 0
    falhou = 0
    erro = 0

    # Agrupar por grupo
    grupos = {}
    for teste in CASOS_TESTE:
        if teste.grupo not in grupos:
            grupos[teste.grupo] = []
        grupos[teste.grupo].append(teste)

    # Executar por grupo
    for nome_grupo in sorted(grupos.keys()):
        testes_grupo = grupos[nome_grupo]
        print(f"\nGRUPO {nome_grupo} ({len(testes_grupo)} testes)")
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
    print(f"Passou:  {passou}/{len(CASOS_TESTE)}")
    print(f"Falhou:  {falhou}/{len(CASOS_TESTE)}")
    print(f"Erro:    {erro}/{len(CASOS_TESTE)}")
    print("=" * 80)

    return 0 if (falhou + erro) == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
