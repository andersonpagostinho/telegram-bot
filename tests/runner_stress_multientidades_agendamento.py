#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS RUNNER — MÚLTIPLAS ENTIDADES EM UMA MENSAGEM

Objetivo:
Testar frases com múltiplas entidades sem GPT real:
- profissional + horário
- profissional + data + horário
- serviço + horário
- negação + alternativa
- incompatibilidade profissional
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


class ContextoMock:
    def __init__(self):
        self.storage = {}

    async def carregar_contexto_temporario(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        atual = copy.deepcopy(self.storage.get(str(user_id), {}))
        atual.update(contexto or {})
        self.storage[str(user_id)] = atual
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
                "Bruna": {
                    "nome": "Bruna",
                    "servicos": ["corte", "escova", "hidratação"],
                    "precos": {"corte": 50.0, "escova": 45.0, "hidratação": 55.0},
                },
                "Carla": {
                    "nome": "Carla",
                    "servicos": ["luzes", "escova", "hidratação"],
                    "precos": {"luzes": 120.0, "escova": 45.0, "hidratação": 55.0},
                },
                "Gloria": {
                    "nome": "Gloria",
                    "servicos": ["corte", "escova"],
                    "precos": {"corte": 50.0, "escova": 45.0},
                },
                "Joana": {
                    "nome": "Joana",
                    "servicos": ["corte", "escova", "coloração"],
                    "precos": {"corte": 50.0, "escova": 40.0, "coloração": 90.0},
                },
            }

        if "ServicosNegocio" in path:
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "escova": {"nome": "escova", "duracao": 40, "preco": 45.0},
                "hidratação": {"nome": "hidratação", "duracao": 45, "preco": 55.0},
                "luzes": {"nome": "luzes", "duracao": 90, "preco": 120.0},
            }

        return {}


class SessionMock:
    async def pegar_sessao(self, user_id):
        return {
            "user_id": user_id,
            "chat_id": user_id,
            "message_id": None,
            "message_thread_id": None,
        }


class GPTMock:
    async def chamar_gpt(self, *args, **kwargs):
        return {"resposta": "mock_resposta"}

    async def gerar_resposta_p1(self, *args, **kwargs):
        return {"resposta": "mock_resposta"}


def texto_resposta_usuario(mensagens):
    if not mensagens:
        return ""

    msg = mensagens[-1]

    if isinstance(msg, dict):
        return str(msg.get("text") or msg.get("texto") or msg.get("mensagem") or "")

    return str(msg)


def resumo_ctx(ctx):
    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "servico": ctx.get("servico"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "data_hora": ctx.get("data_hora"),
        "aguardando_confirmacao_agendamento": ctx.get("aguardando_confirmacao_agendamento"),
        "dados_confirmacao_agendamento": ctx.get("dados_confirmacao_agendamento"),
        "draft_agendamento": ctx.get("draft_agendamento"),
    }


def validar_caso(caso, resultado, mensagens, ctx_final, erro):
    falhas = []
    resposta = texto_resposta_usuario(mensagens)
    exp = caso.get("espera", {})

    if erro:
        falhas.append(f"exceção: {erro['tipo']}: {erro['mensagem']}")

    if exp.get("profissional"):
        obtido = ctx_final.get("profissional_escolhido")
        if obtido != exp["profissional"]:
            falhas.append(
                f"profissional inválido: esperado {exp['profissional']!r}, obtido {obtido!r}"
            )

    if exp.get("servico"):
        obtido = ctx_final.get("servico")
        if obtido != exp["servico"]:
            falhas.append(
                f"serviço inválido: esperado {exp['servico']!r}, obtido {obtido!r}"
            )

    if exp.get("hora"):
        data_hora = ctx_final.get("data_hora") or ""
        if not str(data_hora).endswith(exp["hora"] + ":00") and exp["hora"] not in str(data_hora):
            falhas.append(
                f"hora inválida: esperado {exp['hora']!r}, data_hora obtido {data_hora!r}"
            )

    if exp.get("rejeitar_profissional"):
        prof_esperado = exp.get("profissional_esperado", "Bruna")
        obtido = ctx_final.get("profissional_escolhido")
        if obtido != prof_esperado:
            falhas.append(
                f"profissional incompatível deveria ser rejeitado; esperado manter {prof_esperado!r}, obtido {obtido!r}"
            )

    for termo in caso.get("proibidos", []):
        if termo.lower() in resposta.lower():
            falhas.append(f"resposta contém termo proibido: {termo!r}")

    return {
        "nome": caso["nome"],
        "mensagem": caso["mensagem"],
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
        "resposta_usuario": resposta,
        "resultado": resultado,
        "ctx_final": resumo_ctx(ctx_final),
    }


async def main():
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

    async def sem_conflito_mock(*args, **kwargs):
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }

    async def validar_horario_funcionamento_mock(*args, **kwargs):
        return {
            "permitido": True,
            "aberto": True,
            "inicio": "08:00",
            "fim": "18:00",
            "motivo": "mock",
        }

    if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
        pr.verificar_conflito_e_sugestoes_profissional = sem_conflito_mock

    if hasattr(pr, "validar_horario_funcionamento"):
        pr.validar_horario_funcionamento = validar_horario_funcionamento_mock

    if hasattr(pr, "gerar_resposta_p1"):
        pr.gerar_resposta_p1 = gpt_mock.gerar_resposta_p1

    async def gpt_contexto_mock(*args, **kwargs):
        return await gpt_mock.chamar_gpt(*args, **kwargs)

    if hasattr(pr, "chamar_gpt_com_contexto"):
        pr.chamar_gpt_com_contexto = gpt_contexto_mock

    if hasattr(pr, "chamar_gpt"):
        pr.chamar_gpt = gpt_contexto_mock

    actor_id = "7371670478"
    user_id = actor_id

    casos = [
        {
            "nome": "profissional_horario",
            "mensagem": "com Gloria às 14",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
                "hora": "14:00",
            },
        },
        {
            "nome": "profissional_data_horario",
            "mensagem": "Gloria amanhã às 14",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
                "hora": "14:00",
            },
        },
        {
            "nome": "servico_horario",
            "mensagem": "na verdade quero escova às 10",
            "espera": {
                "profissional": "Bruna",
                "servico": "escova",
                "hora": "10:00",
            },
        },
        {
            "nome": "negacao_alternativa_profissional_horario",
            "mensagem": "Bruna não, pode ser Gloria às 10",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
                "hora": "10:00",
            },
        },
        {
            "nome": "profissional_incompativel_horario",
            "mensagem": "com Carla às 15",
            "espera": {
                "rejeitar_profissional": True,
                "profissional_esperado": "Bruna",
                "servico": "corte",
            },
            "proibidos": [],
        },
    ]

    resultados = []

    for i, caso in enumerate(casos, 1):
        mensagens_enviadas = []

        async def send_mock(*args, **kwargs):
            payload = {
                "args": [str(a) for a in args],
                "kwargs": kwargs,
            }
            mensagens_enviadas.append(payload)
            return {
                "handled": True,
                "already_sent": True,
                "mock_send": payload,
            }

        if hasattr(pr, "_send_and_stop"):
            pr._send_and_stop = send_mock

        if hasattr(pr, "_send_and_stop_ctx"):
            pr._send_and_stop_ctx = send_mock

        ctx_inicial = {
            "estado_fluxo": "agendando",
            "servico": "corte",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-06-05T08:20:00",
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {
                "origem": "confirmacao_pendente",
                "profissional": "Bruna",
                "servico": "corte",
                "data_hora": "2026-06-05T08:20:00",
                "duracao": 30,
                "descricao": "Corte com Bruna",
            },
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte",
                "data_hora": "2026-06-05T08:20:00",
                "modo_prechecagem": True,
            },
        }

        contexto_mock.set_contexto(user_id, ctx_inicial)

        resultado = None
        erro = None

        try:
            resultado = await pr.roteador_principal(
                user_id=user_id,
                mensagem=caso["mensagem"],
                update=None,
                context=None,
            )
        except Exception as e:
            erro = {
                "tipo": type(e).__name__,
                "mensagem": str(e),
            }

        ctx_final = contexto_mock.get_contexto_final(user_id)

        validacao = validar_caso(
            caso=caso,
            resultado=resultado,
            mensagens=mensagens_enviadas,
            ctx_final=ctx_final,
            erro=erro,
        )

        resultados.append(validacao)

        status_symbol = "✅" if validacao["status"] == "SUCESSO" else "❌"
        print(f"{status_symbol} {validacao['nome']}: {validacao['status']}")

        if validacao["falhas"]:
            for falha in validacao["falhas"]:
                print(f"  - {falha}")

    print("\n📊 RESUMO")
    print("=" * 90)

    sucessos = sum(1 for r in resultados if r["status"] == "SUCESSO")
    falhas = sum(1 for r in resultados if r["status"] == "FALHA")

    print(f"TOTAL: {len(resultados)}")
    print(f"SUCESSOS: {sucessos}")
    print(f"FALHAS: {falhas}")

    if falhas:
        print("\n❌ FALHAS:")
        for r in resultados:
            if r["status"] == "FALHA":
                print(f"- {r['nome']} | msg={r['mensagem']!r}")
                for falha in r["falhas"]:
                    print(f"  • {falha}")

    resultado_path = Path(__file__).parent / "resultado_stress_multientidades_agendamento.json"
    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n📄 Resultado salvo em: {resultado_path}")

    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
