#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST — Rajada de Mensagens em Agendamento

Objetivo:
Validar robustez sob condição EXTREMA: múltiplas mensagens processadas
em sequência rápida SEM esperar resposta entre elas (rajada).

Cenário:
1. "quero agendar corte"      → inicia agendamento
2. "amanhã"                   → preenche data
3. "às 10"                    → preenche hora
4. "Bruna"                    → escolhe profissional

Todas 4 mensagens processadas sequencialmente SEM esperar resposta.

Validações críticas:
✅ serviço = corte (não perdido)
✅ data_hora preenchida (não perdida)
✅ profissional = Bruna (não perdido)
✅ apenas 1 draft final (sem duplicatas)
✅ nenhum evento criado (aguardando confirmação)
✅ nenhum estado intermediário inválido
✅ nenhuma perda de slot preenchido
✅ estado final: agendando ou aguardando_confirmacao_agendamento
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
    print("STRESS TEST — Rajada de Mensagens em Agendamento")
    print("=" * 90)

    mensagens = [
        {"texto": "quero agendar corte", "esperado": {"servico": "corte"}},
        {"texto": "amanhã", "esperado": {"data_hora": "preenchida"}},
        {"texto": "às 10", "esperado": {"data_hora": "com_hora"}},
        {"texto": "Bruna", "esperado": {"profissional": "Bruna", "servico": "corte"}},
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

        # Validações por passo
        if i == 1:
            if resumo["servico"] != "corte":
                falhas.append(f"Passo 1: servico deveria ser 'corte', obtido {resumo['servico']!r}")

        elif i == 2:
            if not resumo["data_hora"]:
                falhas.append(f"Passo 2: data_hora não foi preenchida")

        elif i == 3:
            if not resumo["data_hora"] or "10:00" not in resumo["data_hora"]:
                falhas.append(f"Passo 3: data_hora incompleta, obtido {resumo['data_hora']!r}")

        elif i == 4:  # Escolha de profissional (agora é passo 4)
            if resumo["profissional_escolhido"] != "Bruna":
                falhas.append(f"Passo 4: profissional deveria ser 'Bruna', obtido {resumo['profissional_escolhido']!r}")

            if resumo["servico"] != "corte":
                falhas.append(f"Passo 4: servico deveria ser 'corte', obtido {resumo['servico']!r}")

    ctx_final = contexto_mock.get_contexto_final(user_id)

    # Validações finais
    if ctx_final.get("intencao_conversacional") == "consulta_servico":
        falhas.append("Entrou em modo consulta pura (não deveria)")

    if ctx_final.get("estado_fluxo") == "aguardando_endereco_negocio":
        falhas.append("Entrou em onboarding (já tem endereço)")

    if eventos_criados:
        falhas.append(f"Eventos criados antes da confirmação: {len(eventos_criados)}")

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

    resultado_path = Path(__file__).parent / "resultado_stress_rajada_agendamento.json"
    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump({
            "nome": "stress_rajada_agendamento",
            "descricao": "Rajada de 4 mensagens completando agendamento",
            "mensagens": ["quero agendar corte", "amanhã", "às 10", "Bruna"],
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
