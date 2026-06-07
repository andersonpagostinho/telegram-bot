#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DRY_RUN RUNNER CENÁRIO 8 — BUG REAL DE PRODUÇÃO/LOCAL

Objetivo:
Reproduzir o bug onde, durante aguardando_confirmacao_agendamento=True,
o usuário responde "Bruna" e o router responde incorretamente:

"Bruna não atende unha gel.

Quer trocar de profissional?"

Regra esperada:
Se existe confirmação pendente com dados_confirmacao_agendamento,
a mensagem "Bruna" NÃO pode ser interpretada como nova consulta de catálogo.
O serviço oficial continua sendo "corte".
"""

import asyncio
import json
import sys
import types
from datetime import datetime
from pathlib import Path


# ============================================================
# PATH DO PROJETO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ============================================================
# STUB PARA EVITAR IMPORT PESADO DE handlers.bot
# ============================================================

handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub


# ============================================================
# IMPORT DO ROUTER REAL
# ============================================================

import router.principal_router as pr


# ============================================================
# MOCKS INTERNOS SIMPLES
# ============================================================

class ContextoMock:
    def __init__(self):
        self.storage = {}
        self.chamadas = []

    async def carregar_contexto_temporario(self, user_id):
        self.chamadas.append({
            "func": "carregar_contexto_temporario",
            "user_id": str(user_id),
        })
        return dict(self.storage.get(str(user_id), {}))

    async def salvar_contexto_temporario(self, user_id, contexto):
        self.chamadas.append({
            "func": "salvar_contexto_temporario",
            "user_id": str(user_id),
            "contexto": contexto,
        })
        atual = dict(self.storage.get(str(user_id), {}))
        atual.update(contexto or {})
        self.storage[str(user_id)] = atual
        return True

    def get_contexto_final(self, user_id):
        return dict(self.storage.get(str(user_id), {}))


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


# ============================================================
# HELPERS
# ============================================================

def contem_bug(resposta_str):
    texto = (resposta_str or "").lower()
    return (
        "unha gel" in texto
        or "não atende" in texto
        or "nao atende" in texto
        or "quer trocar de profissional" in texto
    )


def extrair_texto_resultado(resultado):
    if resultado is None:
        return ""

    if isinstance(resultado, str):
        return resultado

    if isinstance(resultado, dict):
        partes = []

        for chave in ("text", "texto", "resposta", "mensagem", "message"):
            valor = resultado.get(chave)
            if valor:
                partes.append(str(valor))

        partes.append(json.dumps(resultado, ensure_ascii=False, default=str))
        return "\n".join(partes)

    return str(resultado)


# ============================================================
# MAIN
# ============================================================

async def main():
    contexto_mock = ContextoMock()
    firebase_mock = FirebaseMock()
    session_mock = SessionMock()
    gpt_mock = GPTMock()

    mensagens_enviadas = []

    # --------------------------------------------------------
    # PATCH DOS PONTOS USADOS PELO ROUTER
    # --------------------------------------------------------

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

    async def gpt_contexto_mock(*args, **kwargs):
        return await gpt_mock.chamar_gpt(*args, **kwargs)

    if hasattr(pr, "_send_and_stop"):
        pr._send_and_stop = send_mock

    if hasattr(pr, "_send_and_stop_ctx"):
        pr._send_and_stop_ctx = send_mock

    if hasattr(pr, "chamar_gpt_com_contexto"):
        pr.chamar_gpt_com_contexto = gpt_contexto_mock

    if hasattr(pr, "chamar_gpt"):
        pr.chamar_gpt = gpt_contexto_mock

    # --------------------------------------------------------
    # CENÁRIO REAL
    # --------------------------------------------------------

    actor_id = "7371670478"
    tenant_id = "7394370553"
    user_id = actor_id
    texto_usuario = "Bruna"

    contexto_inicial = {
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

        # Inclui o catálogo no contexto também, para reproduzir
        # resíduo potencial que poderia alimentar bloco tardio.
        "profissionais": [
            {"nome": "Bruna", "servicos": ["corte", "escova", "hidratação"]},
            {"nome": "Larissa", "servicos": ["manicure", "pedicure", "unha gel"]},
        ],
    }

    contexto_mock.storage[user_id] = dict(contexto_inicial)

    print("\n" + "=" * 80)
    print("🧪 RUNNER DRY RUN — CENÁRIO 8")
    print("=" * 80)

    print("\n📋 CTX_INICIAL:")
    print(json.dumps({
        "actor_id": actor_id,
        "tenant_id": tenant_id,
        "estado_fluxo": contexto_inicial.get("estado_fluxo"),
        "aguardando_confirmacao_agendamento": contexto_inicial.get("aguardando_confirmacao_agendamento"),
        "servico": contexto_inicial.get("servico"),
        "profissional_escolhido": contexto_inicial.get("profissional_escolhido"),
        "data_hora": contexto_inicial.get("data_hora"),
        "dados_confirmacao_agendamento": contexto_inicial.get("dados_confirmacao_agendamento"),
        "draft_agendamento": contexto_inicial.get("draft_agendamento"),
    }, indent=2, ensure_ascii=False))

    print(f"\n📝 TEXTO_USUARIO: {repr(texto_usuario)}")

    resultado = None
    erro = None

    try:
        resultado = await pr.roteador_principal(
            user_id=user_id,
            mensagem=texto_usuario,
            update=None,
            context=None,
        )
    except Exception as e:
        erro = {
            "tipo": type(e).__name__,
            "mensagem": str(e),
        }
        print(f"\n❌ EXCEÇÃO: {erro['tipo']}: {erro['mensagem']}")

    contexto_final = contexto_mock.get_contexto_final(user_id)

    texto_resultado = extrair_texto_resultado(resultado)
    texto_sends = json.dumps(mensagens_enviadas, ensure_ascii=False, default=str)
    texto_total = f"{texto_resultado}\n{texto_sends}"

    print("\n🤖 RESPOSTA_ROUTER:")
    print(repr(resultado))

    print("\n📨 MENSAGENS_ENVIADAS:")
    print(json.dumps(mensagens_enviadas, indent=2, ensure_ascii=False, default=str))

    print("\n📋 CTX_FINAL:")
    print(json.dumps({
        "estado_fluxo": contexto_final.get("estado_fluxo"),
        "aguardando_confirmacao_agendamento": contexto_final.get("aguardando_confirmacao_agendamento"),
        "servico": contexto_final.get("servico"),
        "profissional_escolhido": contexto_final.get("profissional_escolhido"),
        "data_hora": contexto_final.get("data_hora"),
        "dados_confirmacao_agendamento": contexto_final.get("dados_confirmacao_agendamento"),
        "draft_agendamento": contexto_final.get("draft_agendamento"),
    }, indent=2, ensure_ascii=False))

    # --------------------------------------------------------
    # ASSERTIONS
    # --------------------------------------------------------

    fail_reasons = []

    print("\n✅ VALIDAÇÕES:")

    if "unha gel" in texto_total.lower():
        fail_reasons.append("resposta/mensagem contém 'unha gel'")
        print("  ❌ resposta não deve conter 'unha gel'")
    else:
        print("  ✅ resposta não contém 'unha gel'")

    if "não atende" in texto_total.lower() or "nao atende" in texto_total.lower():
        fail_reasons.append("resposta/mensagem contém 'não atende'")
        print("  ❌ resposta não deve conter 'não atende'")
    else:
        print("  ✅ resposta não contém 'não atende'")

    if "quer trocar de profissional" in texto_total.lower():
        fail_reasons.append("resposta/mensagem contém 'Quer trocar de profissional?'")
        print("  ❌ resposta não deve conter 'Quer trocar de profissional?'")
    else:
        print("  ✅ resposta não contém 'Quer trocar de profissional?'")

    if contexto_final.get("servico") != "corte":
        fail_reasons.append(
            f"contexto perdeu serviço: esperado 'corte', obtido {repr(contexto_final.get('servico'))}"
        )
        print(f"  ❌ contexto servico deveria ser 'corte', atual={repr(contexto_final.get('servico'))}")
    else:
        print("  ✅ contexto mantém servico='corte'")

    if contexto_final.get("profissional_escolhido") != "Bruna":
        fail_reasons.append(
            f"contexto perdeu profissional: esperado 'Bruna', obtido {repr(contexto_final.get('profissional_escolhido'))}"
        )
        print(
            "  ❌ contexto profissional_escolhido deveria ser 'Bruna', "
            f"atual={repr(contexto_final.get('profissional_escolhido'))}"
        )
    else:
        print("  ✅ contexto mantém profissional_escolhido='Bruna'")

    dados_final = contexto_final.get("dados_confirmacao_agendamento") or {}
    if dados_final.get("servico") != "corte":
        fail_reasons.append(
            f"dados_confirmacao_agendamento perdeu serviço: esperado 'corte', obtido {repr(dados_final.get('servico'))}"
        )
        print(
            "  ❌ dados_confirmacao_agendamento.servico deveria ser 'corte', "
            f"atual={repr(dados_final.get('servico'))}"
        )
    else:
        print("  ✅ dados_confirmacao_agendamento mantém servico='corte'")

    if dados_final.get("profissional") != "Bruna":
        fail_reasons.append(
            f"dados_confirmacao_agendamento perdeu profissional: esperado 'Bruna', obtido {repr(dados_final.get('profissional'))}"
        )
        print(
            "  ❌ dados_confirmacao_agendamento.profissional deveria ser 'Bruna', "
            f"atual={repr(dados_final.get('profissional'))}"
        )
    else:
        print("  ✅ dados_confirmacao_agendamento mantém profissional='Bruna'")

    fluxo_final = contexto_final.get("estado_fluxo")
    if fluxo_final not in ["agendando", "idle", None]:
        fail_reasons.append(
            f"estado_fluxo inesperado: {repr(fluxo_final)}"
        )
        print(f"  ❌ estado_fluxo inesperado: {repr(fluxo_final)}")
    else:
        print(f"  ✅ estado_fluxo aceitável: {repr(fluxo_final)}")

    status = "SUCESSO" if not fail_reasons and erro is None else "FALHA"

    if erro:
        fail_reasons.append(f"exceção: {erro['tipo']}: {erro['mensagem']}")

    print("\n" + "=" * 80)
    print(f"STATUS: {status}")

    if fail_reasons:
        print("\n❌ FAIL_REASON:")
        for i, reason in enumerate(fail_reasons, 1):
            print(f"  {i}. {reason}")

    print("=" * 80 + "\n")

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "cenario": "runner_dry_run_cenario_8",
        "actor_id": actor_id,
        "tenant_id": tenant_id,
        "texto_usuario": texto_usuario,
        "resultado": resultado,
        "mensagens_enviadas": mensagens_enviadas,
        "erro": erro,
        "status": status,
        "fail_reasons": fail_reasons,
        "contexto_inicial": contexto_inicial,
        "contexto_final": contexto_final,
        "chamadas": {
            "contexto": contexto_mock.chamadas,
            "firebase": firebase_mock.chamadas,
            "sessao": session_mock.chamadas,
            "gpt": gpt_mock.chamadas,
        },
        "validacoes": {
            "nao_contem_unha_gel": "unha gel" not in texto_total.lower(),
            "nao_contem_nao_atende": (
                "não atende" not in texto_total.lower()
                and "nao atende" not in texto_total.lower()
            ),
            "nao_contem_trocar_profissional": (
                "quer trocar de profissional" not in texto_total.lower()
            ),
            "contexto_servico_corte": contexto_final.get("servico") == "corte",
            "contexto_profissional_bruna": contexto_final.get("profissional_escolhido") == "Bruna",
            "dados_confirmacao_servico_corte": dados_final.get("servico") == "corte",
            "dados_confirmacao_profissional_bruna": dados_final.get("profissional") == "Bruna",
        },
    }

    caminho = Path(__file__).parent / "resultado_dry_run_cenario_8.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    print(f"📄 Resultado salvo em: {caminho}")

    return 0 if status == "SUCESSO" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)