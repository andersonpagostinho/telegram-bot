#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS RUNNER — CONFIRMAÇÃO DE AGENDAMENTO

Baseado no bug real do Runner 8.

Testa várias respostas humanas possíveis quando o sistema está em:

- aguardando_confirmacao_agendamento=True
- serviço oficial = corte
- profissional oficial = Bruna
- data_hora oficial = 2026-06-05T08:20:00

Objetivo:
Garantir que o router não reinterprete contexto pendente como nova consulta,
não vaze serviço residual e não troque serviço/profissional indevidamente.
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
        self.chamadas.append({
            "func": "carregar_contexto_temporario",
            "user_id": str(user_id),
        })
        return copy.deepcopy(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.chamadas.append({
            "func": "salvar_contexto_temporario",
            "user_id": str(user_id),
            "contexto": copy.deepcopy(contexto),
        })
        atual = copy.deepcopy(self.storage.get(str(user_id), {}))
        atual.update(contexto or {})
        self.storage[str(user_id)] = atual
        return True

    def set_contexto(self, user_id, contexto):
        self.storage[str(user_id)] = copy.deepcopy(contexto)

    def get_contexto_final(self, user_id):
        return copy.deepcopy(self.storage.get(str(user_id), {}))


class FirebaseMock:
    def __init__(self):
        self.chamadas = []

    async def obter_id_dono(self, actor_id):
        self.chamadas.append({
            "func": "obter_id_dono",
            "actor_id": str(actor_id),
        })
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
                "corte": {
                    "nome": "corte",
                    "duracao": 30,
                    "preco": 50.0,
                },
                "escova": {
                    "nome": "escova",
                    "duracao": 40,
                    "preco": 45.0,
                },
                "hidratação": {
                    "nome": "hidratação",
                    "duracao": 45,
                    "preco": 55.0,
                },
                "unha gel": {
                    "nome": "unha gel",
                    "duracao": 90,
                    "preco": 70.0,
                },
            }

        if "Eventos" in str(path):
            return {}

        return {}


class SessionMock:
    def __init__(self):
        self.chamadas = []

    async def pegar_sessao(self, user_id):
        self.chamadas.append({
            "func": "pegar_sessao",
            "user_id": str(user_id),
        })
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
            "As 6",
            "Quero um corte amanhã",
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
            {"nome": "Larissa", "servicos": ["manicure", "pedicure", "unha gel"]},
        ],
    }


def texto_resposta_usuario(mensagens):
    """Extrai APENAS o texto da resposta enviada ao usuário (não contexto/catálogo)."""
    if not mensagens:
        return ""

    partes = []
    for msg in mensagens:
        if isinstance(msg, dict):
            # Procura por "text" (mensagem de texto enviada)
            if "text" in msg:
                partes.append(msg["text"])

    return "\n".join(partes).lower()


def validar_caso(nome, mensagem, resultado, mensagens, ctx_final, erro, expectativas):
    falhas = []

    # 🔒 Verificar termos proibidos APENAS na resposta enviada ao usuário
    resposta_usuario = texto_resposta_usuario(mensagens)

    proibidos = expectativas.get("proibidos", [
        "bruna não atende unha gel",
        "unha gel",
        "não atende",
        "nao atende",
        "quer trocar de profissional",
    ])

    for termo in proibidos:
        if termo.lower() in resposta_usuario:
            falhas.append(f"resposta contém termo proibido: {termo!r}")

    if erro:
        falhas.append(f"exceção: {erro['tipo']}: {erro['mensagem']}")

    servico_esperado = expectativas.get("servico_esperado", "corte")
    profissional_esperado = expectativas.get("profissional_esperado", "Bruna")

    if expectativas.get("manter_servico", True):
        if ctx_final.get("servico") != servico_esperado:
            falhas.append(
                f"servico final inválido: esperado {servico_esperado!r}, obtido {ctx_final.get('servico')!r}"
            )

    if expectativas.get("manter_profissional", True):
        if ctx_final.get("profissional_escolhido") != profissional_esperado:
            falhas.append(
                f"profissional final inválido: esperado {profissional_esperado!r}, "
                f"obtido {ctx_final.get('profissional_escolhido')!r}"
            )

    dados = ctx_final.get("dados_confirmacao_agendamento") or {}

    if expectativas.get("manter_dados_confirmacao", True):
        if dados.get("servico") != servico_esperado:
            falhas.append(
                f"dados_confirmacao.servico inválido: esperado {servico_esperado!r}, obtido {dados.get('servico')!r}"
            )

        if dados.get("profissional") != profissional_esperado:
            falhas.append(
                f"dados_confirmacao.profissional inválido: esperado {profissional_esperado!r}, "
                f"obtido {dados.get('profissional')!r}"
            )

    data_hora_esperada = expectativas.get("data_hora_esperada")
    if data_hora_esperada:
        if ctx_final.get("data_hora") != data_hora_esperada:
            falhas.append(
                f"data_hora inválida: esperado {data_hora_esperada!r}, obtido {ctx_final.get('data_hora')!r}"
            )

    return {
        "nome": nome,
        "mensagem": mensagem,
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
        "resultado": resultado,
        "mensagens_enviadas": mensagens,
        "contexto_final_resumo": {
            "estado_fluxo": ctx_final.get("estado_fluxo"),
            "aguardando_confirmacao_agendamento": ctx_final.get("aguardando_confirmacao_agendamento"),
            "servico": ctx_final.get("servico"),
            "profissional_escolhido": ctx_final.get("profissional_escolhido"),
            "data_hora": ctx_final.get("data_hora"),
            "dados_confirmacao_agendamento": ctx_final.get("dados_confirmacao_agendamento"),
            "draft_agendamento": ctx_final.get("draft_agendamento"),
        },
        "erro": erro,
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
        firebase_mock.chamadas.append({
            "func": "verificar_conflito_e_sugestoes_profissional",
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        })
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }

    async def validar_horario_funcionamento_mock(*args, **kwargs):
        firebase_mock.chamadas.append({
            "func": "validar_horario_funcionamento",
            "args": [str(a) for a in args],
            "kwargs": kwargs,
        })
        return True

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
    tenant_id = "7394370553"
    user_id = actor_id

    casos = [
        {
            "nome": "confirmacao_sim",
            "mensagem": "sim",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "confirmacao_confirmar",
            "mensagem": "confirmar",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "reafirma_profissional_nome",
            "mensagem": "Bruna",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "reafirma_profissional_frase",
            "mensagem": "com a Bruna",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "ajuste_hora_9",
            "mensagem": "às 9",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "ajuste_hora_10",
            "mensagem": "melhor às 10",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "ajuste_hora_8",
            "mensagem": "pode ser às 8",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "troca_profissional_carla",
            "mensagem": "troca para Carla",
            "expectativas": {
                "manter_servico": True,
                "manter_dados_confirmacao": False,
                "proibidos": [
                    "bruna não atende unha gel",
                    "unha gel",
                    "bruna não atende",
                ],
            },
        },
        {
            "nome": "negacao_nao",
            "mensagem": "não",
            "expectativas": {
                "manter_servico": False,
                "manter_profissional": False,
                "manter_dados_confirmacao": False,
            },
        },
        {
            "nome": "cancelar",
            "mensagem": "cancelar",
            "expectativas": {
                "manter_servico": False,
                "manter_profissional": False,
                "manter_dados_confirmacao": False,
            },
        },
        {
            "nome": "alteracao_servico_explicita_escova",
            "mensagem": "na verdade quero escova",
            "expectativas": {
                "manter_servico": False,
                "manter_dados_confirmacao": False,
                "proibidos": [
                    "unha gel",
                    "bruna não atende",
                ],
            },
        },
        {
            "nome": "alteracao_servico_explicita_unha_gel",
            "mensagem": "na verdade quero unha gel",
            "expectativas": {
                "manter_servico": False,
                "manter_dados_confirmacao": False,
                "proibidos": [
                    "bruna não atende corte",
                ],
            },
        },
        {
            "nome": "consulta_preco",
            "mensagem": "quanto custa?",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
        {
            "nome": "consulta_horarios",
            "mensagem": "quais horários tem?",
            "expectativas": {
                "manter_servico": True,
                "manter_profissional": True,
            },
        },
    ]

    resultados = []

    print("\n" + "=" * 90)
    print("🧪 STRESS RUNNER — CONFIRMAÇÃO DE AGENDAMENTO")
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
            nome=caso["nome"],
            mensagem=caso["mensagem"],
            resultado=resultado,
            mensagens=mensagens_enviadas,
            ctx_final=ctx_final,
            erro=erro,
            expectativas=caso["expectativas"],
        )

        resultados.append(validacao)

        if validacao["status"] == "SUCESSO":
            print("STATUS: ✅ SUCESSO")
        else:
            print("STATUS: ❌ FALHA")
            for falha in validacao["falhas"]:
                print(f"  - {falha}")

        if mensagens_enviadas:
            print("RESPOSTA:")
            print(mensagens_enviadas[-1]["args"][-1])

    total = len(resultados)
    falhas = [r for r in resultados if r["status"] != "SUCESSO"]
    sucessos = total - len(falhas)

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

    status_final = "SUCESSO" if not falhas else "FALHA"

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "cenario": "stress_confirmacao_agendamento",
        "status": status_final,
        "total": total,
        "sucessos": sucessos,
        "falhas": len(falhas),
        "resultados": resultados,
        "chamadas": {
            "contexto": contexto_mock.chamadas,
            "firebase": firebase_mock.chamadas,
            "sessao": session_mock.chamadas,
            "gpt": gpt_mock.chamadas,
        },
    }

    caminho = Path(__file__).parent / "resultado_stress_confirmacao_agendamento.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Resultado salvo em: {caminho}")

    return 0 if status_final == "SUCESSO" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)