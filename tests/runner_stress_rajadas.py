#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Rajadas de Mensagens Durante Agendamento

Validar sequência rápida de mensagens durante fluxo ativo.
Cenários: Rajada completa, Correção de hora, Troca de serviço, Incompatibilidade
"""

import asyncio
import copy
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
                "Gloria": {"nome": "Gloria", "servicos": ["corte", "escova"]},
            }
        if "ServicosNegocio" in path:
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "hidratacao": {"nome": "hidratacao", "duracao": 45, "preco": 55.0},
                "escova": {"nome": "escova", "duracao": 40, "preco": 45.0},
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
        "estado_fluxo": ctx.get("estado_fluxo"),
    }


async def executar_cenario(numero, titulo, mensagens, validacoes, contexto_mock, user_id):
    print("\n" + "="*100)
    print(f"CENÁRIO {numero}: {titulo}")
    print("-" * 100)

    contexto_mock.set_contexto(user_id, {})
    contextos = []

    for i, (texto, desc) in enumerate(mensagens, 1):
        print(f"\n[MSG {i}] {desc}")
        print(f"  Entrada: {repr(texto)}")

        ctx_antes = contexto_mock.get_contexto_final(user_id)
        resumo_antes = resumo_ctx(ctx_antes)
        print(f"  Antes:")
        for k, v in resumo_antes.items():
            if v is not None:
                print(f"    {k:25} = {v}")

        try:
            await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None
            )
        except Exception as e:
            print(f"  ❌ Erro: {type(e).__name__}: {str(e)[:80]}")

        ctx_depois = contexto_mock.get_contexto_final(user_id)
        resumo_depois = resumo_ctx(ctx_depois)
        print(f"  Depois:")
        for k, v in resumo_depois.items():
            if v is not None:
                print(f"    {k:25} = {v}")

        contextos.append(resumo_depois)

    print(f"\n[VALIDACOES]")
    falhas = []

    ctx_final = contextos[-1]
    for campo, valor_esperado in validacoes.items():
        valor_obtido = ctx_final.get(campo)

        if callable(valor_esperado):
            if not valor_esperado(valor_obtido):
                falhas.append(f"{campo}: validação customizada falhou")
        else:
            if valor_obtido != valor_esperado:
                falhas.append(f"{campo} != {repr(valor_esperado)} (obtido {repr(valor_obtido)})")

    status = "SUCESSO" if not falhas else "FALHA"
    print(f"  Status: {status}")
    if falhas:
        for f in falhas:
            print(f"    - {f}")

    return status == "SUCESSO", contextos


async def main():
    print("="*100)
    print("STRESS TEST — Rajadas de Mensagens")
    print("="*100)

    firebase_async_mock = FirebaseAsyncMock()
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()

    pr.carregar_contexto_temporario = contexto_mock.carregar_contexto_temporario
    pr.salvar_contexto_temporario = contexto_mock.salvar_contexto_temporario

    if hasattr(pr, "obter_id_dono"):
        pr.obter_id_dono = firebase_mock.obter_id_dono
    if hasattr(pr, "buscar_subcolecao"):
        pr.buscar_subcolecao = firebase_mock.buscar_subcolecao

    async def mock_conflict(*args, **kwargs):
        profissional = kwargs.get("profissional") or (args[2] if len(args) > 2 else None)
        servico = kwargs.get("servico") or (args[3] if len(args) > 3 else None)

        prof_servicos = {
            "Bruna": ["corte", "escova", "hidratacao"],
            "Carla": ["luzes", "escova", "hidratacao"],
            "Gloria": ["corte", "escova"],
        }

        if profissional and servico and profissional in prof_servicos:
            servicos = prof_servicos[profissional]
            incompativel = servico.lower() not in [s.lower() for s in servicos]
            if incompativel:
                return {
                    "conflito": True,
                    "sugestoes": [],
                    "profissional_alternativo": "Bruna"
                }

        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def mock_validar_horario(*args, **kwargs):
        return {"permitido": True, "aberto": True}

    async def mock_validar_profissional(*args, **kwargs):
        profissional = kwargs.get("profissional") or (args[1] if len(args) > 1 else None)
        servico = kwargs.get("servico") or (args[2] if len(args) > 2 else None)

        prof_servicos = {
            "Bruna": ["corte", "escova", "hidratacao"],
            "Carla": ["luzes", "escova", "hidratacao"],
            "Gloria": ["corte", "escova"],
        }

        resultado = {"ok": False, "validos": []}
        if profissional and servico and profissional in prof_servicos:
            servicos = prof_servicos[profissional]
            ok = servico.lower() in [s.lower() for s in servicos]
            resultado = {"ok": ok, "validos": servicos}

        return resultado

    if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
        pr.verificar_conflito_e_sugestoes_profissional = mock_conflict
    if hasattr(pr, "validar_horario_funcionamento"):
        pr.validar_horario_funcionamento = mock_validar_horario
    if hasattr(pr, "validar_profissional_para_servico"):
        pr.validar_profissional_para_servico = mock_validar_profissional

    async def exec_mock(update, context, acao, dados):
        return {"sucesso": True}

    pr.executar_acao_gpt = exec_mock

    resultados = {}

    # CENÁRIO 1: Rajada completa (serviço + data + hora + profissional)
    status1, _ = await executar_cenario(
        1,
        "Rajada completa (serviço + data + hora + profissional)",
        [
            ("quero corte", "MSG1: Serviço"),
            ("amanhã", "MSG2: Data"),
            ("às 10", "MSG3: Hora"),
            ("Bruna", "MSG4: Profissional"),
        ],
        {
            "servico": "corte",
            "draft_servico": "corte",
            "draft_prof": "Bruna",
            "draft_data_hora": lambda v: v and "T10:00" in v,
        },
        contexto_mock,
        "user_cenario_1"
    )
    resultados["Cenário 1"] = "SUCESSO" if status1 else "FALHA"

    # CENÁRIO 2: Correção de hora em rajada
    status2, _ = await executar_cenario(
        2,
        "Correção de hora em rajada (às 10 → às 14)",
        [
            ("quero corte", "MSG1: Serviço"),
            ("amanhã", "MSG2: Data"),
            ("às 10", "MSG3: Hora inicial"),
            ("na verdade às 14", "MSG4: Correção de hora"),
        ],
        {
            "servico": "corte",
            "draft_servico": "corte",
            "draft_data_hora": lambda v: v and "T14:00" in v,
        },
        contexto_mock,
        "user_cenario_2"
    )
    resultados["Cenário 2"] = "SUCESSO" if status2 else "FALHA"

    # CENÁRIO 3: Troca de serviço em rajada
    status3, _ = await executar_cenario(
        3,
        "Troca de serviço em rajada (corte → hidratação)",
        [
            ("quero corte", "MSG1: Serviço inicial"),
            ("amanhã às 10", "MSG2: Data e hora"),
            ("não, hidratação", "MSG3: Troca para hidratação"),
        ],
        {
            "servico": "hidratacao",
            "draft_servico": "hidratacao",
            "draft_data_hora": lambda v: v and "T10:00" in v,
        },
        contexto_mock,
        "user_cenario_3"
    )
    resultados["Cenário 3"] = "SUCESSO" if status3 else "FALHA"

    # CENÁRIO 4: Profissional incompatível em rajada
    status4, ctx4 = await executar_cenario(
        4,
        "Profissional incompatível em rajada (Carla não faz corte)",
        [
            ("quero corte amanhã às 10", "MSG1: Agendamento completo"),
            ("Carla", "MSG2: Profissional incompatível"),
        ],
        {
            "servico": "corte",
            "draft_servico": "corte",
            "draft_data_hora": lambda v: v and "T10:00" in v,
        },
        contexto_mock,
        "user_cenario_4"
    )

    # Validação especial: Carla NÃO deve ser salvo (incompatível)
    if ctx4[-1].get("draft_prof") == "Carla":
        resultados["Cenário 4"] = "FALHA (Carla foi salvo como profissional)"
        status4 = False
    else:
        resultados["Cenário 4"] = "SUCESSO" if status4 else "FALHA"

    # Resumo final
    print("\n" + "="*100)
    print("RESUMO FINAL")
    print("="*100)
    for cenario, status in resultados.items():
        print(f"{cenario:30}: {status}")

    total_sucesso = sum(1 for s in resultados.values() if s == "SUCESSO")
    print(f"\nTotal: {total_sucesso}/{len(resultados)} cenários passaram")

    return 0 if total_sucesso == len(resultados) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
