#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS RUNNER — MUDANÇA LATERAL DE CONTEXTO DURANTE FLUXO ATIVO

Objetivo:
Validar que uma mudança lateral de assunto (pergunta sobre outro serviço)
no meio do agendamento NÃO apaga o draft, NÃO conclui evento,
e permite retomar o fluxo depois.

Fluxo:
1. "quero agendar corte"  → inicia agendamento (servico = corte)
2. "quanto custa escova?" → MUDANÇA LATERAL (pergunta sobre outro serviço)
3. "amanhã"               → retoma agendamento de corte (data)
4. "às 10"                → retoma agendamento de corte (hora)

Validações:
- Após passo 1: servico == "corte"
- Após passo 2:
  * serviço/draft de corte NÃO foram apagados
  * pergunta NÃO troca para escova
  * NÃO cria evento
  * NÃO muda para idle
- Após passo 4:
  * data_hora contém "10:00"
  * serviço final continua "corte"
  * estado em ["agendando", "aguardando_profissional", "aguardando_confirmacao_agendamento"]
  * draft preservado
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


def resumo_ctx(ctx):
    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "servico": ctx.get("servico"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "data_hora": ctx.get("data_hora"),
        "aguardando_confirmacao_agendamento": ctx.get("aguardando_confirmacao_agendamento"),
        "draft_agendamento": ctx.get("draft_agendamento"),
    }


def log_contexto_passo(passo, ctx):
    """Log estruturado do contexto após cada passo"""
    resumo = resumo_ctx(ctx)
    print(f"   📊 [CTX PASSO {passo}]")
    print(f"      servico: {resumo['servico']!r}")
    print(f"      data_hora: {resumo['data_hora']!r}")
    print(f"      estado: {resumo['estado_fluxo']!r}")
    print(f"      draft: {'OK' if resumo['draft_agendamento'] else 'VAZIO'}")


def validar_mudanca_contexto(ctx_final, ctx_passo_2, falhas_acumuladas):
    """Validar que mudança lateral não apaga o fluxo"""
    falhas = list(falhas_acumuladas)

    # Validação pós-passo 1: serviço iniciado
    servico_final = ctx_final.get("servico")
    draft_final = ctx_final.get("draft_agendamento") or {}
    if servico_final != "corte" and draft_final.get("servico") != "corte":
        falhas.append(f"serviço não mantido: esperado 'corte', obtido servico={servico_final!r}, draft={draft_final.get('servico')!r}")

    # Validação pós-passo 2: contexto NÃO foi alterado para escova
    if ctx_passo_2:
        servico_passo_2 = ctx_passo_2.get("servico")
        draft_passo_2 = ctx_passo_2.get("draft_agendamento") or {}

        if servico_passo_2 == "escova" or draft_passo_2.get("servico") == "escova":
            falhas.append("pergunta de preço MUDOU o serviço para escova (não deve mudar)")

        if not servico_passo_2 and not draft_passo_2.get("servico"):
            falhas.append("pergunta de preço LIMPOU o serviço (não deve limpar)")

    # Validação pós-passo 4: data_hora completa
    data_hora = ctx_final.get("data_hora") or ""
    if "10:00" not in str(data_hora):
        falhas.append(f"hora inválida: esperado '10:00', obtido {data_hora!r}")

    # Validação: estado válido
    estado = ctx_final.get("estado_fluxo")
    if estado == "idle" or estado is None:
        falhas.append(f"estado é idle ou None: esperado um estado ativo, obtido {estado!r}")

    estados_validos = [
        "agendando",
        "aguardando_profissional",
        "aguardando_confirmacao_agendamento"
    ]
    if estado and estado not in estados_validos:
        falhas.append(f"estado inválido: esperado um de {estados_validos}, obtido {estado!r}")

    # Validar que draft não foi limpo
    if not draft_final:
        falhas.append("draft_agendamento foi limpo (não deve ser)")
    elif draft_final.get("servico") != "corte":
        falhas.append(f"draft serviço inválido: esperado 'corte', obtido {draft_final.get('servico')!r}")

    return {
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
        "ctx_final": resumo_ctx(ctx_final),
    }


async def main():
    firebase_async_mock = FirebaseAsyncMock()

    # Mock Firebase ANTES de importar utils
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    # Mock contexto temporário
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

    # Mock de endereço já existente
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

    # Mock para interceptar criação de evento
    eventos_criados = []

    async def criar_evento_mock(*args, **kwargs):
        eventos_criados.append({"args": args, "kwargs": kwargs})
        return {"id": "mock_evento_id", "criado": True}

    if hasattr(pr, "add_evento_por_gpt"):
        pr.add_evento_por_gpt = criar_evento_mock

    actor_id = "7371670478"
    user_id = actor_id

    # Contexto inicial vazio
    ctx_inicial = {}

    # Mensagens da rajada
    mensagens_rajada = [
        {"texto": "quero agendar corte", "descricao": "Inicia fluxo com serviço"},
        {"texto": "quanto custa escova?", "descricao": "Mudança lateral: pergunta sobre outro serviço"},
        {"texto": "amanhã", "descricao": "Retoma agendamento de corte com data"},
        {"texto": "às 10", "descricao": "Retoma agendamento de corte com hora"},
    ]

    mensagens_enviadas = []
    falhas_acumuladas = []
    ctx_passo_2 = None

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

    contexto_mock.set_contexto(user_id, ctx_inicial)

    print("\n" + "=" * 90)
    print("STRESS RUNNER - MUDANÇA LATERAL DE CONTEXTO DURANTE FLUXO ATIVO")
    print("=" * 90)

    for i, msg_data in enumerate(mensagens_rajada, 1):
        texto = msg_data["texto"]
        descricao = msg_data["descricao"]

        print(f"\nPASSO {i}: {descricao}")
        print(f"   Mensagem: {repr(texto)}")

        resultado = None
        erro = None

        try:
            resultado = await pr.roteador_principal(
                user_id=user_id,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            erro = {
                "tipo": type(e).__name__,
                "mensagem": str(e),
            }
            falhas_acumuladas.append(f"Passo {i} falhou: {e}")

        if erro:
            print(f"   ❌ ERRO: {erro['mensagem']}")
        else:
            print(f"   ✓ Processado")

        # Log de contexto após cada passo
        ctx_atual = contexto_mock.get_contexto_final(user_id)
        log_contexto_passo(i, ctx_atual)

        # Capturar contexto após passo 2 para validação
        if i == 2:
            ctx_passo_2 = copy.deepcopy(ctx_atual)

    # Contexto final
    ctx_final = contexto_mock.get_contexto_final(user_id)

    # Validação final
    validacao = validar_mudanca_contexto(
        ctx_final=ctx_final,
        ctx_passo_2=ctx_passo_2,
        falhas_acumuladas=falhas_acumuladas,
    )

    # Verificar que nenhum evento foi criado
    if eventos_criados:
        validacao["falhas"].append(f"Nenhum evento deveria ser criado, mas {len(eventos_criados)} foram criados")

    print("\n" + "=" * 90)
    print("VALIDAÇÃO FINAL")
    print("=" * 90)

    status_symbol = "✅" if validacao["status"] == "SUCESSO" else "❌"
    print(f"{status_symbol} {validacao['status']}")

    if validacao["falhas"]:
        print("\nFalhas:")
        for falha in validacao["falhas"]:
            print(f"  • {falha}")

    print("\n" + "=" * 90)
    print("RESUMO")
    print("=" * 90)

    sucessos = 1 if validacao["status"] == "SUCESSO" else 0
    falhas = 1 if validacao["status"] == "FALHA" else 0

    print(f"TOTAL: 1")
    print(f"SUCESSOS: {sucessos}")
    print(f"FALHAS: {falhas}")

    if falhas:
        print("\nFAIL FALHAS:")
        print(f"- mudanca_contexto_fluxo_ativo")
        for falha in validacao["falhas"]:
            print(f"  • {falha}")

    resultado_path = Path(__file__).parent / "resultado_stress_mudanca_contexto_fluxo_ativo.json"
    resultado_completo = {
        "nome": "mudanca_contexto_fluxo_ativo",
        "descricao": "Mudança lateral de assunto não deve apagar o fluxo ativo",
        "mensagens": [m["texto"] for m in mensagens_rajada],
        "mudanca_lateral_no_passo": 2,
        "endereco_mockado": True,
        "status": validacao["status"],
        "falhas": validacao["falhas"],
        "ctx_final": validacao["ctx_final"],
        "eventos_criados": len(eventos_criados),
    }

    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump([resultado_completo], f, ensure_ascii=False, indent=2)

    print(f"\nResultado salvo em: {resultado_path}")

    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
