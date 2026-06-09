#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Substituicao de Slots Durante Agendamento Ativo

Cenario 1: Servico muda (corte -> hidratacao)
- MSG1: "quero agendar corte amanha as 10"
- MSG2: "na verdade quero hidratacao"

Validacoes:
- servico final = hidratacao
- data_hora preservada = 2026-06-10
- draft_agendamento = {'servico': 'hidratacao', 'data_hora': ...}
"""

import asyncio
import copy
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub

import router.principal_router as pr
import services.firebase_service_async as firebase_async


class FirebaseAsyncMock:
    def __init__(self):
        self.dados = {}

    async def buscar_dado_em_path(self, path):
        return self.dados.get(path)

    async def salvar_dado_em_path(self, path, dados):
        self.dados[path] = dados
        return True

    async def atualizar_dado_em_path(self, path, dados):
        if path in self.dados:
            self.dados[path].update(dados)
        else:
            self.dados[path] = dados.copy()
        return True


class ContextoMock:
    def __init__(self):
        self.storage = {}

    async def carregar_contexto_temporario(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto or {})
        return True

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))


class FirebaseMock:
    async def obter_id_dono(self, actor_id):
        return "7394370553"

    async def buscar_subcolecao(self, path):
        path = str(path)
        if "Profissionais" in path:
            return {
                "Bruna": {"nome": "Bruna", "servicos": ["corte", "escova", "hidratacao"]},
                "Carla": {"nome": "Carla", "servicos": ["luzes", "escova", "hidratacao"]},
            }
        if "ServicosNegocio" in path:
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "hidratacao": {"nome": "hidratacao", "duracao": 45, "preco": 55.0},
                "manicure": {"nome": "manicure", "duracao": 40, "preco": 30.0},
                "luzes": {"nome": "luzes", "duracao": 90, "preco": 120.0},
            }
        return {}


class SessionMock:
    async def pegar_sessao(self, user_id):
        return {"user_id": user_id, "chat_id": user_id}


class GPTMock:
    async def chamar_gpt(self, *args, **kwargs):
        return {"resposta": "mock"}


def resumo_ctx(ctx):
    draft = ctx.get("draft_agendamento") or {}
    return {
        "servico": ctx.get("servico"),
        "data_hora": ctx.get("data_hora"),
        "profissional": ctx.get("profissional_escolhido"),
        "draft_servico": draft.get("servico"),
        "draft_data_hora": draft.get("data_hora"),
        "draft_prof": draft.get("profissional"),
    }


async def main():
    print("="*100)
    print("STRESS TEST — Substituicao de Slots")
    print("="*100)

    firebase_async_mock = FirebaseAsyncMock()
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()
    session_mock = SessionMock()
    gpt_mock = GPTMock()

    pr.carregar_contexto_temporario = contexto_mock.carregar_contexto_temporario
    pr.salvar_contexto_temporario = contexto_mock.salvar_contexto_temporario

    if hasattr(pr, "pegar_sessao"):
        pr.pegar_sessao = session_mock.pegar_sessao
    if hasattr(pr, "obter_id_dono"):
        pr.obter_id_dono = firebase_mock.obter_id_dono
    if hasattr(pr, "buscar_subcolecao"):
        pr.buscar_subcolecao = firebase_mock.buscar_subcolecao

    dono_id = "7394370553"
    firebase_async_mock.dados[f"Clientes/{dono_id}/configuracao/dados_negocio"] = {
        "endereco": {"rua": "Test"}
    }

    async def mock_conflict(*args, **kwargs):
        return {"conflito": False}

    if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
        pr.verificar_conflito_e_sugestoes_profissional = mock_conflict
    if hasattr(pr, "validar_horario_funcionamento"):
        pr.validar_horario_funcionamento = mock_conflict
    if hasattr(pr, "chamar_gpt"):
        pr.chamar_gpt = mock_conflict

    async def exec_mock(update, context, acao, dados):
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    # CENARIO 1: Servico muda
    print("\nCENARIO 1: Servico muda (corte -> hidratacao)")
    print("-" * 100)

    user_id = "user_cenario_1"
    contexto_mock.set_contexto(user_id, {})

    mensagens = [
        ("quero agendar corte amanha as 10", "MSG1: Agendamento corte"),
        ("na verdade quero hidratacao", "MSG2: Muda para hidratacao"),
    ]

    contextos = []

    for i, (texto, desc) in enumerate(mensagens, 1):
        print(f"\n[MSG {i}] {desc}")
        print(f"  Entrada: {repr(texto)}")

        try:
            await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None
            )
        except Exception as e:
            print(f"  Erro: {type(e).__name__}")

        ctx = contexto_mock.get_contexto_final(user_id)
        resumo = resumo_ctx(ctx)
        contextos.append(resumo)

        print(f"  Contexto:")
        for k, v in resumo.items():
            print(f"    {k:20} = {v}")

    # Validacoes
    print("\n[VALIDACOES]")
    falhas = []

    if contextos[0].get("servico") != "corte":
        falhas.append(f"MSG1: servico != 'corte' (obtido {contextos[0].get('servico')})")

    if contextos[1].get("servico") != "hidratacao":
        falhas.append(f"MSG2: servico != 'hidratacao' (obtido {contextos[1].get('servico')})")

    if contextos[0].get("data_hora") is None:
        falhas.append("MSG1: data_hora nao foi preenchida")

    if contextos[1].get("data_hora") != contextos[0].get("data_hora"):
        falhas.append(f"MSG2: data_hora foi alterada")

    if contextos[1].get("draft_servico") != "hidratacao":
        falhas.append(f"MSG2: draft_servico != 'hidratacao' (obtido {contextos[1].get('draft_servico')})")

    if falhas:
        print("  Status: FALHA")
        for f in falhas:
            print(f"    - {f}")
        return 1
    else:
        print("  Status: SUCESSO")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
