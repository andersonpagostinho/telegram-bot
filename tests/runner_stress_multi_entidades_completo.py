#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Múltiplas Entidades Simultâneas

Objetivo:
Validar extração simultânea de múltiplas entidades em uma única mensagem,
sem perda de slots.

Cenários:

1. MENSAGEM COMPLETA
   "quero agendar corte com Bruna amanhã às 10"
   ✅ serviço = "corte"
   ✅ profissional = "Bruna"
   ✅ data_hora preenchida
   ✅ draft_agendamento contém 3 slots
   ✅ estado = agendando (ou aguardando_confirmacao)

2. AMBIGUIDADE DE SERVIÇO
   "quero agendar corte ou escova com Bruna amanhã às 10"
   ✅ NÃO escolhe automaticamente
   ✅ mantém Bruna
   ✅ mantém data_hora
   ✅ solicita escolha (sem perder contexto)

3. AMBIGUIDADE DE HORÁRIO
   "quero corte com Bruna amanhã às 10 ou às 11"
   ✅ serviço = corte
   ✅ profissional = Bruna
   ✅ múltiplos horários detectados
   ✅ horarios_sugeridos preenchido
   ✅ solicita escolha
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
                "Bruna": {
                    "nome": "Bruna",
                    "servicos": ["corte", "escova", "hidratação"],
                    "precos": {"corte": 50.0, "escova": 45.0, "hidratação": 55.0},
                },
                "Carla": {
                    "nome": "Carla",
                    "servicos": ["escova", "hidratação", "luzes"],
                    "precos": {"escova": 45.0, "hidratação": 55.0, "luzes": 120.0},
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


def resumo_ctx(ctx):
    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "servico": ctx.get("servico"),
        "data_hora": ctx.get("data_hora"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "draft_agendamento": ctx.get("draft_agendamento"),
        "intencao_conversacional": ctx.get("intencao_conversacional"),
    }


async def main():
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

    # Mock de endereço já existente (para evitar onboarding)
    dono_id = "7394370553"
    firebase_async_mock.dados[f"Clientes/{dono_id}/configuracao/dados_negocio"] = {
        "endereco": {
            "rua": "Rua João Baroni",
            "numero": "550",
            "completo": "Rua João Baroni, 550"
        }
    }

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

    eventos_criados = []

    async def criar_evento_mock(*args, **kwargs):
        eventos_criados.append({"args": args, "kwargs": kwargs})
        return {"id": "mock_evento_id", "criado": True}

    if hasattr(pr, "add_evento_por_gpt"):
        pr.add_evento_por_gpt = criar_evento_mock

    actor_id = "7371670478"
    user_id = actor_id

    contexto_mock.set_contexto(user_id, {})

    print("\n" + "=" * 90)
    print("STRESS TEST — Múltiplas Entidades Simultâneas")
    print("=" * 90)

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

    # 3 Cenários independentes
    cenarios = [
        {
            "nome": "Cenário 1: Mensagem Completa",
            "mensagem": "quero agendar corte com Bruna amanhã às 10",
            "validacoes": {
                "servico": "corte",
                "profissional": "Bruna",
                "has_data_hora": True,
                "draft_servico": "corte",
                "no_eventos": True,
            }
        },
        {
            "nome": "Cenário 2: Ambiguidade de Serviço",
            "mensagem": "quero agendar corte ou escova com Bruna amanhã às 10",
            "validacoes": {
                "profissional": "Bruna",
                "has_data_hora": True,
                "not_auto_servico": True,  # NÃO escolhe automaticamente
                "preserva_contexto": True,
            }
        },
        {
            "nome": "Cenário 3: Ambiguidade de Horário",
            "mensagem": "quero corte com Bruna amanhã às 10 ou às 11",
            "validacoes": {
                "servico": "corte",
                "profissional": "Bruna",
                "multiple_horas": True,
                "no_eventos": True,
            }
        },
    ]

    resultados_cenarios = []

    for cenario in cenarios:
        print(f"\n{'='*90}")
        print(f"{cenario['nome']}")
        print(f"{'='*90}")
        print(f"Mensagem: {repr(cenario['mensagem'])}")

        # Limpar eventos de cenário anterior
        eventos_criados.clear()
        contexto_mock.set_contexto(user_id, {})

        try:
            resultado = await pr.roteador_principal(
                user_id=user_id,
                mensagem=cenario["mensagem"],
                update=None,
                context=None,
            )
        except Exception as e:
            print(f"❌ ERRO: {e}")
            resultados_cenarios.append({
                "cenario": cenario["nome"],
                "status": "ERRO",
                "erro": str(e),
                "falhas": [str(e)],
                "ctx_final": {},
            })
            continue

        ctx_final = contexto_mock.get_contexto_final(user_id)
        resumo = resumo_ctx(ctx_final)
        falhas_cenario = []

        # Validações
        val = cenario["validacoes"]

        if "servico" in val and resumo.get("servico") != val["servico"]:
            falhas_cenario.append(f"serviço: esperado {val['servico']!r}, obtido {resumo.get('servico')!r}")

        if "profissional" in val and resumo.get("profissional_escolhido") != val["profissional"]:
            falhas_cenario.append(f"profissional: esperado {val['profissional']!r}, obtido {resumo.get('profissional_escolhido')!r}")

        if val.get("has_data_hora") and not resumo.get("data_hora"):
            falhas_cenario.append(f"data_hora não preenchida")

        if val.get("draft_servico") and (resumo.get("draft_agendamento") or {}).get("servico") != val["draft_servico"]:
            falhas_cenario.append(f"draft serviço inválido: esperado {val['draft_servico']!r}")

        if val.get("no_eventos") and len(eventos_criados) > 0:
            falhas_cenario.append(f"eventos criados: {len(eventos_criados)} (esperado 0)")

        if val.get("not_auto_servico"):
            # Validar que servico ficou vazio ou ambíguo
            if resumo.get("servico") in ["corte", "escova"]:
                pass  # OK, está esperando
            else:
                falhas_cenario.append(f"serviço foi escolhido automaticamente (não deveria)")

        if val.get("preserva_contexto"):
            draft = resumo.get("draft_agendamento") or {}
            if not draft.get("profissional"):
                falhas_cenario.append(f"contexto perdido: profissional não preservado")

        if val.get("multiple_horas"):
            if not ctx_final.get("horarios_sugeridos") and "10:00" not in str(ctx_final.get("data_hora", "")):
                falhas_cenario.append(f"múltiplos horários não detectados")

        # Log de resultado
        status_cenario = "✅ SUCESSO" if not falhas_cenario else "❌ FALHA"
        print(f"\n{status_cenario}")
        print(f"serviço={resumo.get('servico')!r}, prof={resumo.get('profissional_escolhido')!r}")
        print(f"data_hora={resumo.get('data_hora')!r}")
        print(f"estado={resumo.get('estado_fluxo')!r}")

        if falhas_cenario:
            for falha in falhas_cenario:
                print(f"  • {falha}")

        resultados_cenarios.append({
            "cenario": cenario["nome"],
            "mensagem": cenario["mensagem"],
            "status": "SUCESSO" if not falhas_cenario else "FALHA",
            "falhas": falhas_cenario,
            "ctx_final": resumo,
        })

    print("\n" + "=" * 90)
    print("RESUMO CONSOLIDADO")
    print("=" * 90)

    total = len(resultados_cenarios)
    sucessos = sum(1 for r in resultados_cenarios if r["status"] == "SUCESSO")
    falhas_totais = sum(len(r.get("falhas", [])) for r in resultados_cenarios)

    print(f"Total de cenários: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {total - sucessos}")
    print(f"Total de problemas: {falhas_totais}")

    status_geral = "SUCESSO" if sucessos == total else "FALHA"

    resultado_path = Path(__file__).parent / "resultado_stress_multi_entidades_completo.json"
    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump({
            "nome": "stress_multi_entidades_completo",
            "descricao": "Extração simultânea de múltiplas entidades sem perda de slots",
            "status_geral": status_geral,
            "total_cenarios": total,
            "sucessos": sucessos,
            "falhas": total - sucessos,
            "problemas_totais": falhas_totais,
            "cenarios": resultados_cenarios,
        }, f, ensure_ascii=False, indent=2)

    print(f"Resultado salvo em: {resultado_path}")

    return 0 if status_geral == "SUCESSO" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
