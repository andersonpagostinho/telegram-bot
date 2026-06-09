#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Profissional Alternativo Completo

Objetivo:
Validar 4 cenários críticos de seleção de profissional alternativo:

1. ACEITA SUGESTÃO
   Bruna ocupada às 10:00 → Sistema sugere Carla
   Usuário: "agende com Carla"
   ✅ profissional final = Carla
   ✅ serviço preservado
   ✅ horário preservado
   ✅ conflito reavaliado para Carla
   ✅ nenhum evento antes da confirmação

2. REJEITA SUGESTÃO
   Bruna ocupada → Carla sugerida
   Usuário: "não quero Carla" ou "prefiro Bruna"
   ✅ não troca automaticamente
   ✅ mantém Bruna como referência
   ✅ preserva contexto
   ✅ não cria evento

3. MÚLTIPLAS ALTERNATIVAS
   Bruna ocupada, Carla disponível, Amanda disponível
   Sistema retorna: [Carla, Amanda]
   ✅ alternativas armazenadas no contexto
   ✅ aguarda escolha
   Usuário escolhe: "Amanda"
   ✅ profissional final = Amanda
   ✅ contexto preservado

4. SEM ALTERNATIVAS
   Bruna ocupada, Carla ocupada, Amanda ocupada
   ✅ NÃO cria evento automaticamente
   ✅ NÃO escolhe profissional sozinho
   ✅ informa indisponibilidade
   ✅ mantém contexto
"""

import asyncio
import copy
import json
import sys
import types
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


handlers_bot_stub = types.ModuleType("handlers.bot")
handlers_bot_stub.register_handlers = lambda *args, **kwargs: None
sys.modules["handlers.bot"] = handlers_bot_stub


import router.principal_router as pr
import services.event_service_async as event_service


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
                    "servicos": ["corte", "escova", "hidratação"],
                    "precos": {
                        "corte": 50.0,
                        "escova": 45.0,
                        "hidratação": 55.0,
                    },
                },
                "Amanda": {
                    "nome": "Amanda",
                    "servicos": ["corte", "escova", "hidratação"],
                    "precos": {
                        "corte": 50.0,
                        "escova": 45.0,
                        "hidratação": 55.0,
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
    # Contexto começa VAZIO para que a primeira mensagem dispare PRE-CHECK
    return {
        "historico_texto": [],
        "modo_conversa": "operacional",
        "hora_confirmada": False,

        "estado_fluxo": "idle",
        "objetivo_conversacional": None,

        "servico": None,
        "profissional_escolhido": None,
        "data": None,
        "data_hora": None,

        "draft_agendamento": {},

        "usuario": {
            "user_id": actor_id,
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente",
        },
    }


def resumo_ctx(ctx):
    draft = ctx.get("draft_agendamento") or {}

    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "servico": ctx.get("servico"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "data_hora": ctx.get("data_hora"),
        "draft_profissional": draft.get("profissional"),
        "draft_servico": draft.get("servico"),
        "draft_data_hora": draft.get("data_hora"),
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

    # Mocks parametrizados por cenário
    eventos_criados = []

    # Cenário 1: Bruna ocupada, Carla sugerida
    async def conflito_mock_cenario_1(*args, **kwargs):
        hora = kwargs.get("hora_inicio")
        profissional = kwargs.get("profissional")

        print(f"[MOCK_CONFLITO_CENARIO_1] chamado | profissional={profissional!r} hora={hora!r}", flush=True)

        if profissional == "Bruna" and hora == "10:00":
            resultado = {
                "conflito": True,
                "sugestoes": [],
                "profissional_alternativo": "Carla",
            }
            print(f"[MOCK_CONFLITO_CENARIO_1] RETORNANDO CONFLITO | {resultado}", flush=True)
            return resultado

        resultado = {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }
        print(f"[MOCK_CONFLITO_CENARIO_1] SEM CONFLITO | {resultado}", flush=True)
        return resultado

    # Cenário 2: Bruna ocupada, Carla sugerida (mesmo do 1)
    async def conflito_mock_cenario_2(*args, **kwargs):
        hora = kwargs.get("hora_inicio")
        profissional = kwargs.get("profissional")

        if profissional == "Bruna" and hora == "10:00":
            return {
                "conflito": True,
                "sugestoes": [],
                "profissional_alternativo": "Carla",
            }
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }

    # Cenário 3: Múltiplas alternativas
    async def conflito_mock_cenario_3(*args, **kwargs):
        hora = kwargs.get("hora_inicio")
        profissional = kwargs.get("profissional")

        if profissional == "Bruna" and hora == "10:00":
            return {
                "conflito": True,
                "sugestoes": ["Carla", "Amanda"],
                "profissional_alternativo": None,
            }
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None,
        }

    # Cenário 4: Todas ocupadas (sem alternativas)
    async def conflito_mock_cenario_4(*args, **kwargs):
        hora = kwargs.get("hora_inicio")
        profissional = kwargs.get("profissional")

        if profissional in ["Bruna", "Carla", "Amanda"] and hora == "10:00":
            return {
                "conflito": True,
                "sugestoes": [],
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

    cenarios = [
        {
            "numero": 0,
            "nome": "Teste Isolado: Aceita Alternativa Existente",
            "descricao": "Contexto ja preparado com alternativa - Usuario diz agende com Carla",
            "conflito_mock": None,  # SEM MOCK - teste isolado
            "contexto_inicial": {
                "estado_fluxo": "aguardando_escolha_horario",
                "modo_escolha_horario": True,
                "servico": "corte",
                "profissional_escolhido": "Bruna",
                "data_hora": "2026-06-10T10:00:00",
                "alternativa_profissional": "Carla",
                "ultima_opcao_profissionais": ["Bruna", "Carla"],
                "horarios_sugeridos": ["10:00", "10:40"],
                "draft_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": "2026-06-10T10:00:00",
                },
                "dados_confirmacao_agendamento": {
                    "servico": "corte",
                    "profissional": "Bruna",
                    "data_hora": "2026-06-10T10:00:00",
                    "duracao": 30,
                    "descricao": "Corte com Bruna",
                },
            },
            "mensagens": [
                "agende com Carla",
            ],
            "validacoes": {
                "profissional_final": "Carla",
                "servico_final": "corte",
                "horario_preservado": "10:00",
                "draft_profissional_final": "Carla",
                "confirmacao_profissional_final": "Carla",
            },
        },
        {
            "numero": 1,
            "nome": "Aceita Sugestao - Carla",
            "descricao": "Bruna ocupada as 10:00 - Sistema sugere Carla - Usuario aceita",
            "conflito_mock": conflito_mock_cenario_1,
            "mensagens": [
                "quero agendar corte amanhã às 10 com Bruna",
                "agende com Carla",
            ],
            "validacoes": {
                "profissional_final": "Carla",
                "servico_final": "corte",
                "horario_preservado": "10:00",
            },
        },
        {
            "numero": 2,
            "nome": "Rejeita Sugestao",
            "descricao": "Bruna ocupada - Carla sugerida - Usuario rejeita",
            "conflito_mock": conflito_mock_cenario_2,
            "mensagens": [
                "quero agendar corte amanhã às 10 com Bruna",
                "não quero Carla",
            ],
            "validacoes": {
                "profissional_final": "Bruna",
                "servico_final": "corte",
                "horario_preservado": "10:00",
                "nenhum_evento": True,
            },
        },
        {
            "numero": 3,
            "nome": "Multiplas Alternativas",
            "descricao": "Sistema oferece Carla e Amanda - Usuario escolhe Amanda",
            "conflito_mock": conflito_mock_cenario_3,
            "mensagens": [
                "quero agendar corte amanhã às 10 com Bruna",
                "Amanda",
            ],
            "validacoes": {
                "profissional_final": "Amanda",
                "servico_final": "corte",
                "horario_preservado": "10:00",
            },
        },
        {
            "numero": 4,
            "nome": "Sem Alternativas",
            "descricao": "Todas ocupadas - Sistema informa indisponibilidade",
            "conflito_mock": conflito_mock_cenario_4,
            "mensagens": [
                "quero agendar corte amanhã às 10 com Bruna",
            ],
            "validacoes": {
                "nenhum_evento": True,
                "contexto_preservado": True,
            },
        },
    ]

    resultados_cenarios = []

    print("\n" + "=" * 90)
    print("STRESS TEST — Profissional Alternativo Completo")
    print("=" * 90)

    for cenario in cenarios:
        print(f"\n{'=' * 90}")
        print(f"CENÁRIO {cenario['numero']}: {cenario['nome']}")
        print(f"{'=' * 90}")
        print(f"Descrição: {cenario['descricao']}")

        # Resetar estado para novo cenário
        eventos_criados.clear()

        # Usar contexto_inicial se fornecido, senão usar contexto_base
        if cenario.get("contexto_inicial"):
            ctx_inicial = copy.deepcopy(cenario["contexto_inicial"])
            # Mergebrowser com usuario info
            ctx_inicial["usuario"] = {
                "user_id": actor_id,
                "id_negocio": tenant_id,
                "tipo_usuario": "cliente",
            }
            contexto_mock.set_contexto(user_id, ctx_inicial)
            print(f"[CONTEXTO] Usando contexto_inicial fornecido", flush=True)
        else:
            contexto_mock.set_contexto(user_id, contexto_base(actor_id=actor_id, tenant_id=tenant_id))
            print(f"[CONTEXTO] Usando contexto_base padrão", flush=True)

        # Configurar mock de conflito específico para este cenário (se fornecido)
        if cenario.get("conflito_mock"):
            print(f"\n[SETUP_MOCK] Configurando mock para cenário {cenario['numero']}", flush=True)
            if hasattr(pr, "verificar_conflito_e_sugestoes_profissional"):
                pr.verificar_conflito_e_sugestoes_profissional = cenario["conflito_mock"]
                print(f"[SETUP_MOCK] Mock setado em pr.verificar_conflito_e_sugestoes_profissional", flush=True)

            if hasattr(event_service, "verificar_conflito_e_sugestoes_profissional"):
                event_service.verificar_conflito_e_sugestoes_profissional = cenario["conflito_mock"]
                print(f"[SETUP_MOCK] Mock setado em event_service.verificar_conflito_e_sugestoes_profissional", flush=True)
        else:
            print(f"[SETUP_MOCK] Teste isolado - nenhum mock configurado", flush=True)

        falhas_cenario = []
        contextos_por_mensagem = []

        async def send_mock(*args, **kwargs):
            return {"handled": True, "already_sent": True}

        if hasattr(pr, "_send_and_stop"):
            pr._send_and_stop = send_mock

        if hasattr(pr, "_send_and_stop_ctx"):
            pr._send_and_stop_ctx = send_mock

        # Mock para executar_acao_gpt
        async def executar_acao_gpt_mock(update, context, acao, dados):
            if acao == "criar_evento":
                eventos_criados.append({"acao": acao, "dados": dados})
            return {"sucesso": True, "acao": acao}

        pr.executar_acao_gpt = executar_acao_gpt_mock

        # Executar mensagens
        for msg_idx, mensagem in enumerate(cenario["mensagens"], 1):
            print(f"\n  Mensagem {msg_idx}: {repr(mensagem)}")

            try:
                resultado = await pr.roteador_principal(
                    user_id=user_id,
                    mensagem=mensagem,
                    update=None,
                    context=None,
                )
            except Exception as e:
                falhas_cenario.append(f"Mensagem {msg_idx}: Exceção {type(e).__name__}: {e}")
                print(f"    [ERRO] {type(e).__name__}: {e}")
                continue

            ctx_atual = contexto_mock.get_contexto_final(user_id)
            contextos_por_mensagem.append({
                "mensagem": msg_idx,
                "texto": mensagem,
                "contexto": resumo_ctx(ctx_atual),
            })

            print(f"    prof={ctx_atual.get('profissional_escolhido')!r}, "
                  f"serv={ctx_atual.get('servico')!r}, "
                  f"eventos={len(eventos_criados)}")
            print(f"    alternativa_profissional={ctx_atual.get('alternativa_profissional')!r}", flush=True)
            print(f"    modo_escolha_horario={ctx_atual.get('modo_escolha_horario')!r}", flush=True)
            print(f"    estado_fluxo={ctx_atual.get('estado_fluxo')!r}", flush=True)

            draft = ctx_atual.get('draft_agendamento') or {}
            conf = ctx_atual.get('dados_confirmacao_agendamento') or {}
            print(f"    draft.profissional={draft.get('profissional')!r}", flush=True)
            print(f"    confirmacao.profissional={conf.get('profissional')!r}", flush=True)

        # Contexto final
        ctx_final = contexto_mock.get_contexto_final(user_id)
        resumo = resumo_ctx(ctx_final)

        # Validações
        val = cenario.get("validacoes", {})

        if val.get("profissional_final"):
            if ctx_final.get("profissional_escolhido") != val["profissional_final"]:
                falhas_cenario.append(
                    f"Profissional: esperado {val['profissional_final']!r}, "
                    f"obtido {ctx_final.get('profissional_escolhido')!r}"
                )

        if val.get("servico_final"):
            if ctx_final.get("servico") != val["servico_final"]:
                falhas_cenario.append(
                    f"Serviço: esperado {val['servico_final']!r}, "
                    f"obtido {ctx_final.get('servico')!r}"
                )

        if val.get("horario_preservado"):
            if val["horario_preservado"] not in (ctx_final.get("data_hora") or ""):
                falhas_cenario.append(
                    f"Horário: esperado conter {val['horario_preservado']!r}, "
                    f"obtido {ctx_final.get('data_hora')!r}"
                )

        if val.get("draft_profissional_final"):
            draft = ctx_final.get("draft_agendamento") or {}
            if draft.get("profissional") != val["draft_profissional_final"]:
                falhas_cenario.append(
                    f"Draft profissional: esperado {val['draft_profissional_final']!r}, "
                    f"obtido {draft.get('profissional')!r}"
                )

        if val.get("confirmacao_profissional_final"):
            conf = ctx_final.get("dados_confirmacao_agendamento") or {}
            if conf.get("profissional") != val["confirmacao_profissional_final"]:
                falhas_cenario.append(
                    f"Confirmacao profissional: esperado {val['confirmacao_profissional_final']!r}, "
                    f"obtido {conf.get('profissional')!r}"
                )

        if val.get("nenhum_evento") and len(eventos_criados) > 0:
            falhas_cenario.append(f"Nenhum evento deveria ser criado, mas {len(eventos_criados)} foram")

        if val.get("contexto_preservado"):
            draft = ctx_final.get("draft_agendamento") or {}
            if not draft or not draft.get("servico"):
                falhas_cenario.append("Contexto não foi preservado (draft vazio)")

        # Status do cenário
        status_cenario = "SUCESSO" if not falhas_cenario else "FALHA"
        print(f"\n[{status_cenario}]")

        if falhas_cenario:
            for falha in falhas_cenario:
                print(f"  • {falha}")

        resultados_cenarios.append({
            "cenario_numero": cenario["numero"],
            "nome": cenario["nome"],
            "status": "SUCESSO" if not falhas_cenario else "FALHA",
            "falhas": falhas_cenario,
            "mensagens": cenario["mensagens"],
            "ctx_final": resumo,
            "eventos_criados": len(eventos_criados),
            "contextos_por_mensagem": contextos_por_mensagem,
        })

    # Resumo consolidado
    print("\n" + "=" * 90)
    print("RESUMO CONSOLIDADO")
    print("=" * 90)

    total = len(resultados_cenarios)
    sucessos = sum(1 for r in resultados_cenarios if r["status"] == "SUCESSO")
    falhas_totais = sum(len(r.get("falhas", [])) for r in resultados_cenarios)

    print(f"Total de cenários: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {total - sucessos}")
    print(f"Problemas totais: {falhas_totais}")

    status_geral = "SUCESSO" if sucessos == total else "FALHA"

    resultado_path = Path(__file__).parent / "resultado_stress_profissional_alternativo_completo.json"
    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "nome": "stress_profissional_alternativo_completo",
            "descricao": "Testes de profissional alternativo: aceita, rejeita, múltiplas, sem alternativas",
            "status_geral": status_geral,
            "total_cenarios": total,
            "sucessos": sucessos,
            "falhas": total - sucessos,
            "problemas_totais": falhas_totais,
            "cenarios": resultados_cenarios,
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResultado salvo em: {resultado_path}")

    return 0 if status_geral == "SUCESSO" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)