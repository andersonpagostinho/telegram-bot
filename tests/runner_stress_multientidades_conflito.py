#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS RUNNER — MÚLTIPLAS ENTIDADES COM CONFLITO

Objetivo:
Validar alterações múltiplas quando o horário solicitado
entra em conflito e o motor precisa sugerir alternativa.

Casos:
- serviço + horário com conflito
- profissional + horário com conflito
- troca de profissional para horário ocupado

Base:
corte com Bruna em 2026-06-05T08:20:00
"""

import asyncio
import copy
import json
import sys
import types
from datetime import datetime
from pathlib import Path



# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub


import router.principal_router as pr


class ContextoMock:
    def __init__(self):
        self.storage = {}
        self.chamadas = []

    async def carregar_contexto_temporario(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        atual = copy.deepcopy(self.storage.get(str(user_id), {}))
        atual.update(contexto or {})
        self.storage[str(user_id)] = atual
        self.chamadas.append({
            "func": "salvar_contexto_temporario",
            "user_id": str(user_id),
            "contexto": copy.deepcopy(contexto),
        })
        return True

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))


class FirebaseMock:
    def __init__(self):
        self.chamadas = []

    async def obter_id_dono(self, actor_id):
        return "7394370553"

    async def buscar_subcolecao(self, path):
        self.chamadas.append({
            "func": "buscar_subcolecao",
            "path": str(path),
        })

        if "Profissionais" in str(path):
            return {
                "Amanda": {
                    "nome": "Amanda",
                    "servicos": ["coloração", "luzes", "botox capilar"],
                    "precos": {
                        "luzes": 120.0,
                        "botox capilar": 150.0,
                        "coloração": 95.0,
                    },
                },
                "Bruna": {
                    "nome": "Bruna",
                    "servicos": ["corte", "escova", "hidratação"],
                    "precos": {
                        "corte": 50.0,
                        "escova": 45.0,
                        "hidratação": 55.0,
                    },
                },
                "Carla": {
                    "nome": "Carla",
                    "servicos": ["Luzes", "escova", "hidratação"],
                    "precos": {
                        "luzes": 120.0,
                        "escova": 45.6,
                    },
                    "duracoes": {
                        "luzes": 90,
                    },
                    "servicos_detalhe": {
                        "luzes": {
                            "duracao": 90,
                            "preco": 120.0,
                        }
                    },
                },
                "Gloria": {
                    "nome": "Gloria",
                    "servicos": ["corte", "escova"],
                },
                "Joana": {
                    "nome": "Joana",
                    "servicos": ["corte", "escova", "coloração"],
                    "precos": {
                        "corte": 50.0,
                        "escova": 40.0,
                        "coloração": 90.0,
                    },
                },
                "Larissa": {
                    "nome": "Larissa",
                    "servicos": ["manicure", "pedicure", "unha gel"],
                    "precos": {
                        "manicure": 30.0,
                        "pedicure": 30.0,
                        "unha gel": 70.0,
                    },
                },
            }

        if "ServicosNegocio" in str(path):
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "escova": {"nome": "escova", "duracao": 40, "preco": 45.0},
                "hidratação": {"nome": "hidratação", "duracao": 45, "preco": 55.0},
                "unha gel": {"nome": "unha gel", "duracao": 90, "preco": 70.0},
            }

        if "Eventos" in str(path):
            return {}

        return {}


class SessionMock:
    async def pegar_sessao(self, user_id):
        return {
            "estado_fluxo": "agendando",
            "draft": {},
            "ultima_acao": None,
        }


class GPTMock:
    def __init__(self):
        self.chamadas = []

    async def gerar_resposta_p1(self, *args, **kwargs):
        self.chamadas.append({
            "func": "gerar_resposta_p1",
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        })
        return "Mock P1 interceptado"

    async def chamar_gpt(self, *args, **kwargs):
        self.chamadas.append({
            "func": "chamar_gpt",
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        })
        return {
            "acao": "responder",
            "resposta": "Mock GPT interceptado",
            "dados": {},
        }


def contexto_base(actor_id, tenant_id):
    return {
        "historico_texto": [
            "Quero um corte amanhã",
            "Bruna",
        ],
        "modo_conversa": "operacional",
        "hora_confirmada": True,

        "estado_fluxo": "agendando",
        "objetivo_conversacional": "preparar_prechecagem_agendamento",

        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data": "2026-06-05",
        "data_hora": "2026-06-05T08:20:00",
        "data_sem_hora": False,

        "ultima_consulta": {
            "data_hora": "2026-06-05T08:20:00",
        },

        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data": "2026-06-05",
            "data_hora": "2026-06-05T08:20:00",
            "modo_prechecagem": True,
        },

        "interpretacao_conversacional": {
            "intencao": "ajuste_incremental",
            "confianca": 90,
            "tipo_ajuste": "horario",
            "entidades": {
                "horario": "06:00",
            },
        },

        "intencao_conversacional": "ajuste_incremental",
        "confianca_intencao_conversacional": 90,
        "tipo_ajuste_incremental": "horario",

        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "origem": "confirmacao_pendente",
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-06-05T08:20:00",
            "duracao": 30,
            "descricao": "Corte com Bruna",
        },

        "ultima_opcao_profissionais": ["Bruna"],

        "usuario": {
            "user_id": actor_id,
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente",
        },

        "profissionais": [
            {"nome": "Bruna", "servicos": ["corte", "escova", "hidratação"]},
            {"nome": "Gloria", "servicos": ["corte", "escova"]},
            {"nome": "Joana", "servicos": ["corte", "escova", "coloração"]},
            {"nome": "Carla", "servicos": ["escova", "hidratação", "luzes"]},
            {"nome": "Larissa", "servicos": ["manicure", "pedicure", "unha gel"]},
        ],
    }


def texto_resposta_usuario(mensagens):
    partes = []

    for msg in mensagens:
        if not isinstance(msg, dict):
            continue

        if "text" in msg:
            partes.append(str(msg["text"]))

        args = msg.get("args") or []
        if args:
            partes.append(str(args[-1]))

    return "\n".join(partes).lower()


def resumo_ctx(ctx):
    dados = ctx.get("dados_confirmacao_agendamento") or {}
    draft = ctx.get("draft_agendamento") or {}

    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "aguardando_confirmacao_agendamento": ctx.get("aguardando_confirmacao_agendamento"),
        "servico": ctx.get("servico"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "data_hora": ctx.get("data_hora"),
        "draft": {
            "servico": draft.get("servico"),
            "profissional": draft.get("profissional"),
            "data_hora": draft.get("data_hora"),
        },
        "dados_confirmacao": {
            "servico": dados.get("servico"),
            "profissional": dados.get("profissional"),
            "data_hora": dados.get("data_hora"),
            "duracao": dados.get("duracao"),
            "descricao": dados.get("descricao"),
        },
    }


def validar_caso(caso, resultado, mensagens, ctx_final, erro):
    falhas = []
    resposta = texto_resposta_usuario(mensagens)
    ctx_resumo = resumo_ctx(ctx_final)

    proibidos = caso.get("proibidos", [
        "bruna não atende unha gel",
        "bruna nao atende unha gel",
    ])

    for termo in proibidos:
        if termo.lower() in resposta:
            falhas.append(f"resposta contém termo proibido: {termo!r}")

    if erro:
        falhas.append(f"exceção: {erro['tipo']}: {erro['mensagem']}")

    exp = caso.get("espera", {})

    if exp.get("nao_criar_evento_direto"):
        if "executando criar_evento direto" in resposta:
            falhas.append("criou evento direto quando deveria ajustar")

    if exp.get("manter_servico") is not False:
        servico_esperado = exp.get("servico", "corte")
        if ctx_final.get("servico") != servico_esperado:
            falhas.append(
                f"servico final inválido: esperado {servico_esperado!r}, obtido {ctx_final.get('servico')!r}"
            )

    if exp.get("profissional"):
        if ctx_final.get("profissional_escolhido") != exp["profissional"]:
            falhas.append(
                f"profissional final inválido: esperado {exp['profissional']!r}, "
                f"obtido {ctx_final.get('profissional_escolhido')!r}"
            )

    if exp.get("hora"):
        esperado_suffix = f"T{exp['hora']}:00"
        data_hora = ctx_final.get("data_hora") or ""
        if not str(data_hora).startswith("2026-06-05T") or not str(data_hora).endswith(f"{exp['hora']}:00"):
            falhas.append(
                f"data_hora não preservou data com hora esperada {exp['hora']}: obtido {data_hora!r}"
            )

    if exp.get("encerrar_fluxo"):
        if ctx_final.get("aguardando_confirmacao_agendamento") is True:
            falhas.append("deveria encerrar confirmação pendente, mas continuou aguardando")

    if caso["nome"] == "servico_horario_com_conflito":

        if "10:40" not in resposta:
            falhas.append(
                "não sugeriu horário alternativo esperado"
            )

        if ctx_final.get("data_hora") == "2026-06-05T10:00:00":
            falhas.append(
                "gravou horário em conflito"
            )

    return {
        "nome": caso["nome"],
        "mensagem": caso["mensagem"],
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
        "resposta_usuario": resposta,
        "resultado": resultado,
        "ctx_final": ctx_resumo,
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

    async def conflito_mock(*args, **kwargs):

        hora = kwargs.get("hora_inicio")
        servico = kwargs.get("servico")
        profissional = kwargs.get("profissional")

        if (
            servico == "escova"
            and profissional == "Bruna"
            and hora == "10:00"
        ):
            return {
                "conflito": True,
                "sugestoes": [
                    "10:40",
                    "11:20",
                    "12:00",
                ],
                "profissional_alternativo": None,
            }

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
        pr.verificar_conflito_e_sugestoes_profissional = conflito_mock

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
    tenant_id = "7394370553"
    user_id = actor_id

    casos = [
        {
            "nome": "troca_para_gloria",
            "mensagem": "troca para Gloria",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
            },
        },
        {
            "nome": "troca_para_gloria_14",
            "mensagem": "troca para Gloria às 14",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
                "hora": "14:00",
                "nao_criar_evento_direto": True,
            },
        },
        {
            "nome": "troca_para_carla_incompativel",
            "mensagem": "troca para Carla",
            "espera": {
                "profissional": "Bruna",
                "servico": "corte",
            },
            "proibidos": [
                "bruna não atende unha gel",
                "unha gel",
            ],
        },
        {
            "nome": "melhor_amanha",
            "mensagem": "melhor amanhã",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
        {
            "nome": "mais_cedo",
            "mensagem": "mais cedo",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
        {
            "nome": "mais_tarde",
            "mensagem": "mais tarde",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
        {
            "nome": "nao",
            "mensagem": "não",
            "espera": {
                "manter_servico": False,
                "encerrar_fluxo": True,
            },
        },
        {
            "nome": "cancelar",
            "mensagem": "cancelar",
            "espera": {
                "manter_servico": False,
                "encerrar_fluxo": True,
            },
        },
        {
            "nome": "amanha_mesmo_horario",
            "mensagem": "amanhã no mesmo horário",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
        {
            "nome": "qualquer_horario",
            "mensagem": "qualquer horário",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
        {
            "nome": "qualquer_profissional",
            "mensagem": "qualquer profissional",
            "espera": {
                "servico": "corte",
            },
        },
        {
            "nome": "gloria_mais_tarde",
            "mensagem": "com Gloria mais tarde",
            "espera": {
                "profissional": "Gloria",
                "servico": "corte",
            },
        },
        {
            "nome": "servico_horario_com_conflito",
            "mensagem": "na verdade quero escova às 10",
            "espera": {
                "servico": "corte",
                "profissional": "Bruna",
            },
        },
    ]

    resultados = []

    print("\n" + "=" * 90)
    print("🧪 STRESS RUNNER — CONFIRMAÇÃO PENDENTE + AJUSTES")
    print("=" * 90)

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

        contexto_mock.set_contexto(
            user_id,
            contexto_base(actor_id=actor_id, tenant_id=tenant_id),
        )

        resultado = None
        erro = None

        print("\n" + "-" * 90)
        print(f"CASO {i:02d}: {caso['nome']}")
        print(f"MSG: {caso['mensagem']!r}")

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

        print(f"STATUS: {'✅ SUCESSO' if validacao['status'] == 'SUCESSO' else '❌ FALHA'}")

        if validacao["falhas"]:
            for falha in validacao["falhas"]:
                print(f"  - {falha}")

        if mensagens_enviadas:
            print("RESPOSTA:")
            print(mensagens_enviadas[-1]["args"][-1])

        print("CTX_FINAL:")
        print(json.dumps(validacao["ctx_final"], indent=2, ensure_ascii=False, default=str))

    total = len(resultados)
    falhas = [r for r in resultados if r["status"] != "SUCESSO"]
    sucessos = total - len(falhas)
    status_final = "SUCESSO" if not falhas else "FALHA"

    print("\n" + "=" * 90)
    print("📊 RESUMO")
    print("=" * 90)
    print(f"TOTAL: {total}")
    print(f"SUCESSOS: {sucessos}")
    print(f"FALHAS: {len(falhas)}")

    if falhas:
        print("\n❌ FALHAS:")
        for f in falhas:
            print(f"- {f['nome']} | msg={f['mensagem']!r}")
            for falha in f["falhas"]:
                print(f"  • {falha}")

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "cenario": "stress_confirmacao_pendente_ajustes",
        "status": status_final,
        "total": total,
        "sucessos": sucessos,
        "falhas": len(falhas),
        "resultados": resultados,
    }

    caminho = Path(__file__).parent / "resultado_stress_confirmacao_pendente_ajustes.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Resultado salvo em: {caminho}")

    return 0 if status_final == "SUCESSO" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)