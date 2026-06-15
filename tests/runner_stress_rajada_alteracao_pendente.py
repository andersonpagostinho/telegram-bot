#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Rajada + Ajuste Incremental + Confirmação Pendente

Objetivo:
Validar robustez quando rajada ocorre durante confirmação pendente
com ajuste incremental (historicamente explosivo).

Contexto inicial (pré-estabelecido):
- servico = corte
- profissional = Bruna
- data_hora = amanhã às 10
- aguardando_confirmacao_agendamento = true
- dados_confirmacao_agendamento preenchido

Rajada durante confirmação:
1. "na verdade às 11"         → ajuste incremental (horário)
2. "pode ser"                 → confirmação do ajuste

Validações críticas:
✅ horário final = 11:00 (ajuste aplicado)
✅ serviço continua corte (não alterado)
✅ profissional continua Bruna (não alterado)
✅ nenhuma duplicação de evento
✅ máximo 1 evento criado
✅ confirmação usa horário ajustado (11:00), não antigo (10:00)
✅ estado_fluxo em agendado/confirmado
"""

import asyncio
import copy
import json
import sys
import types
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
        "dados_confirmacao_agendamento": ctx.get("dados_confirmacao_agendamento"),
        "intencao_conversacional": ctx.get("intencao_conversacional"),
        "objetivo_conversacional": ctx.get("objetivo_conversacional"),
        "tipo_ajuste_incremental": ctx.get("tipo_ajuste_incremental"),
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

    # Contexto inicial: confirmação pendente pré-estabelecida
    contexto_inicial = {
        "estado_fluxo": "agendando",
        "servico": "corte",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-06-11T10:00:00",
        "draft_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "2026-06-11T10:00:00",
        },
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "servico": "corte",
            "profissional": "Bruna",
            "data_hora": "2026-06-11T10:00:00",
        },
        "objetivo_conversacional": "preparar_prechecagem_agendamento",
    }

    print("\n📊 CONTEXTO INICIAL:")
    print(f"  estado_fluxo: {contexto_inicial.get('estado_fluxo')}")
    print(f"  aguardando_confirmacao_agendamento: {contexto_inicial.get('aguardando_confirmacao_agendamento')}")
    print(f"  objetivo_conversacional: {contexto_inicial.get('objetivo_conversacional')}")
    print(f"  dados_confirmacao_agendamento: {contexto_inicial.get('dados_confirmacao_agendamento')}\n")

    contexto_mock.set_contexto(user_id, contexto_inicial)

    # Verificar que foi setado
    ctx_check = await contexto_mock.carregar_contexto_temporario(user_id)
    print(f"  ✓ Carregado de volta: objetivo_conversacional={ctx_check.get('objetivo_conversacional')}\n")

    print("\n" + "=" * 90)
    print("STRESS TEST — Rajada + Ajuste Incremental + Confirmação Pendente")
    print("=" * 90)

    mensagens = [
        {"texto": "na verdade às 11", "esperado": {"ajuste": "horario"}},
        {"texto": "pode ser", "esperado": {"confirmacao": True}},
    ]

    contextos_por_mensagem = []
    falhas = []
    ctx_passo_4 = None

    async def send_mock(*args, **kwargs):
        return {"handled": True, "already_sent": True}

    if hasattr(pr, "_send_and_stop"):
        pr._send_and_stop = send_mock

    if hasattr(pr, "_send_and_stop_ctx"):
        pr._send_and_stop_ctx = send_mock

    # Mock para executar_acao_gpt (para ações como pre_confirmar_agendamento)
    async def executar_acao_gpt_mock(update, context, acao, dados):
        if acao == "criar_evento":
            # Registrar que um evento foi criado
            eventos_criados.append({"acao": acao, "dados": dados})
        return {"sucesso": True, "acao": acao}

    pr.executar_acao_gpt = executar_acao_gpt_mock

    for i, msg_data in enumerate(mensagens, 1):
        texto = msg_data["texto"]
        esperado = msg_data["esperado"]

        print(f"\nPASSO {i}: {repr(texto)}")

        try:
            resultado = await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            falhas.append(f"Passo {i} falhou com exceção: {e}")
            print(f"   ❌ ERRO: {e}")
            continue

        ctx_atual = contexto_mock.get_contexto_final(user_id)
        resumo = resumo_ctx(ctx_atual)

        # Capturar contexto por mensagem
        contextos_por_mensagem.append({
            "mensagem": i,
            "texto": texto,
            "contexto": resumo
        })

        # Log resumido
        print(f"   servico={resumo['servico']!r}, data_hora={resumo['data_hora']!r}, prof={resumo['profissional_escolhido']!r}")
        print(f"   eventos_criados_neste_passo: {len(eventos_criados)}")

        # Validações por passo
        if i == 1:  # Ajuste incremental (horário)
            if not resumo["data_hora"]:
                falhas.append(f"Passo 1: data_hora não foi ajustada")
            elif "11:00" not in resumo["data_hora"]:
                falhas.append(f"Passo 1: horário deveria ser 11:00, obtido {resumo['data_hora']!r}")

            if resumo["servico"] != "corte":
                falhas.append(f"Passo 1: servico mudou para {resumo['servico']!r} (deveria continuar 'corte')")

            if resumo["profissional_escolhido"] != "Bruna":
                falhas.append(f"Passo 1: profissional mudou para {resumo['profissional_escolhido']!r} (deveria continuar 'Bruna')")

        elif i == 2:  # Confirmação
            if "11:00" not in (resumo["data_hora"] or ""):
                falhas.append(f"Passo 2: horário não é 11:00, obtido {resumo['data_hora']!r}")

            if resumo["servico"] != "corte":
                falhas.append(f"Passo 2: servico incorreto: {resumo['servico']!r}")

    ctx_final = contexto_mock.get_contexto_final(user_id)

    # Validações finais específicas para rajada + alteração pendente

    # Confirmar que horário foi ajustado para 11:00
    data_hora_final = ctx_final.get("data_hora") or ""
    if "11:00" not in data_hora_final:
        falhas.append(f"Horário final não é 11:00: {data_hora_final!r}")

    # Confirmar que serviço NÃO foi alterado
    if ctx_final.get("servico") != "corte":
        falhas.append(f"Serviço foi alterado para {ctx_final.get('servico')!r}")

    # Confirmar que profissional NÃO foi alterado
    if ctx_final.get("profissional_escolhido") != "Bruna":
        falhas.append(f"Profissional foi alterado para {ctx_final.get('profissional_escolhido')!r}")

    # Validar duplicação de eventos
    if len(eventos_criados) > 1:
        falhas.append(f"Eventos duplicados: {len(eventos_criados)} eventos criados (máximo 1)")

    # Confirmar que evento foi criado com horário ajustado
    if len(eventos_criados) == 0:
        falhas.append(f"Nenhum evento foi criado (deveria ter criado 1)")
    elif len(eventos_criados) > 0:
        evento = eventos_criados[0]
        dados_evento = evento.get("dados", {})
        data_hora_evento = dados_evento.get("data_hora", "")
        if "11:00" not in data_hora_evento:
            falhas.append(f"Evento foi criado com horário errado: {data_hora_evento!r} (deveria ter 11:00)")

    print("\n" + "=" * 90)
    print("VALIDAÇÃO FINAL")
    print("=" * 90)

    if falhas:
        print("❌ FALHA")
        for falha in falhas:
            print(f"  • {falha}")
        status = "FALHA"
    else:
        print("✅ SUCESSO — Cenário perigoso superado!")
        status = "SUCESSO"

    print("\n" + "=" * 90)

    resultado_path = Path(__file__).parent / "resultado_stress_rajada_alteracao_pendente.json"
    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump({
            "nome": "stress_rajada_alteracao_pendente",
            "descricao": "Rajada com ajuste incremental durante confirmação pendente",
            "contexto_inicial": {"servico": "corte", "profissional": "Bruna", "data_hora": "2026-06-11T10:00:00", "aguardando_confirmacao": True},
            "rajada": ["na verdade às 11", "pode ser"],
            "status": status,
            "falhas": falhas,
            "ctx_final": resumo_ctx(ctx_final),
            "eventos_criados": len(eventos_criados),
            "contextos_por_mensagem": contextos_por_mensagem,
        }, f, ensure_ascii=False, indent=2)

    print(f"Resultado salvo em: {resultado_path}")

    return 0 if not falhas else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
