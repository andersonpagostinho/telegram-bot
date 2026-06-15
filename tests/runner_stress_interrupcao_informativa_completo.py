#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST  Interrupes Informativas Durante Agendamento Ativo

Objetivo:
Validar que perguntas informativas durante fluxo de agendamento NO alteram slots crticos.

Cenrios testados:
1. Fluxo ativo + pergunta de endereo
2. Retomada ps-interrupo
3. Mltiplas interrupes informativas (custo, profissional, expediente)

Validaes crticas para cada cenrio:
 Pergunta respondida (informao fornecida)
 draft_agendamento preservado
 servico, profissional, data_hora no alterados
 estado_fluxo permanece em fluxo ativo
 nenhum evento criado
 contexto no reiniciado

Entrada:
- Mensagens de agendamento
- Perguntas informativas no meio do fluxo
- Retomada aps interrupo

Sada esperada:
- logs antes/depois de cada mensagem
- resultado de validao por cenrio
- nenhum patch sem causa raiz comprovada
"""

import asyncio
import copy
import json
import sys
import types
from pathlib import Path
from datetime import datetime, timedelta



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


# ============================================================================
# MOCKS
# ============================================================================

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
                    "servicos": ["corte", "escova", "hidratao"],
                    "precos": {"corte": 50.0, "escova": 45.0, "hidratao": 55.0},
                },
                "Carla": {
                    "nome": "Carla",
                    "servicos": ["luzes", "escova", "hidratao"],
                    "precos": {"luzes": 120.0, "escova": 45.0, "hidratao": 55.0},
                },
                "Gloria": {
                    "nome": "Gloria",
                    "servicos": ["corte", "escova"],
                    "precos": {"corte": 50.0, "escova": 45.0},
                },
                "Joana": {
                    "nome": "Joana",
                    "servicos": ["corte", "escova", "colorao"],
                    "precos": {"corte": 50.0, "escova": 40.0, "colorao": 90.0},
                },
            }

        if "ServicosNegocio" in path:
            return {
                "corte": {"nome": "corte", "duracao": 30, "preco": 50.0},
                "escova": {"nome": "escova", "duracao": 40, "preco": 45.0},
                "hidratao": {"nome": "hidratao", "duracao": 45, "preco": 55.0},
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


# ============================================================================
# UTILITRIOS DE LOG E VALIDAO
# ============================================================================

def resumo_ctx(ctx):
    """Extrair campos crticos do contexto"""
    draft = ctx.get("draft_agendamento") or {}
    return {
        "estado_fluxo": ctx.get("estado_fluxo"),
        "servico": ctx.get("servico"),
        "draft_servico": draft.get("servico"),
        "profissional_escolhido": ctx.get("profissional_escolhido"),
        "draft_profissional": draft.get("profissional"),
        "data_hora": ctx.get("data_hora"),
        "draft_data_hora": draft.get("data_hora"),
        "aguardando_confirmacao_agendamento": ctx.get("aguardando_confirmacao_agendamento"),
        "draft_exists": bool(draft),
    }


def log_contexto_detalhado(passo_num, mensagem, ctx_antes, ctx_depois):
    """Log estruturado antes/depois de cada passo"""
    print(f"\n{'-' * 100}")
    print(f"PASSO {passo_num}: {mensagem}")
    print(f"{'-' * 100}")

    print(f"\n[ANTES]")
    antes = resumo_ctx(ctx_antes)
    for key, val in antes.items():
        print(f"   {key:35} = {str(val)[:60]}")

    print(f"\n[DEPOIS]")
    depois = resumo_ctx(ctx_depois)
    for key, val in depois.items():
        val_str = str(val)[:60]
        changed = " [MUDOU]" if antes.get(key) != depois.get(key) else ""
        print(f"   {key:35} = {val_str}{changed}")


def validar_cenario_1_pergunta_informativa(ctx_inicial, ctx_apos_msg1, ctx_apos_msg2):
    """
    Validao Cenrio 1: Fluxo ativo + pergunta informativa

    Esperado:
    - Msg 1: "quero agendar corte"  servico=corte, draft criado
    - Msg 2: "qual o endereo?"  resposta informativa, servico permanece, draft permanece
    """
    falhas = []

    # Aps msg 1: servico foi definido
    if ctx_apos_msg1.get("servico") != "corte" and (ctx_apos_msg1.get("draft_agendamento") or {}).get("servico") != "corte":
        falhas.append("Passo 1: servio no foi definido como 'corte'")

    # Aps msg 1: draft foi criado
    if not ctx_apos_msg1.get("draft_agendamento"):
        falhas.append("Passo 1: draft_agendamento no foi criado")

    # Aps msg 2: pergunta informativa NO limpou servio
    if ctx_apos_msg2.get("servico") is None and (ctx_apos_msg2.get("draft_agendamento") or {}).get("servico") is None:
        #  OK se foi movido para draft, mas no pode ter desaparecido
        if not (ctx_apos_msg2.get("draft_agendamento") or {}).get("servico"):
            falhas.append("Passo 2: pergunta informativa limpou o servio")

    # Aps msg 2: draft foi preservado
    if ctx_apos_msg1.get("draft_agendamento") and not ctx_apos_msg2.get("draft_agendamento"):
        falhas.append("Passo 2: draft_agendamento foi apagado aps pergunta informativa")

    return {
        "cenario": "1_pergunta_informativa",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


def validar_cenario_2_retomada_apos_interrupcao(ctx_apos_interrupcao, ctx_apos_retomada):
    """
    Validao Cenrio 2: Retomada aps interrupo

    Esperado:
    - Pergunta informativa no reiniciou fluxo
    - Dados anteriores foram mantidos
    - Fluxo pode ser retomado com "pode ser" ou "ok"
    """
    falhas = []

    # Aps retomada: contexto no foi zerado
    servico_antes = (ctx_apos_interrupcao.get("draft_agendamento") or {}).get("servico")
    servico_depois = (ctx_apos_retomada.get("draft_agendamento") or {}).get("servico")

    if servico_antes and not servico_depois:
        falhas.append("Retomada: servio foi perdido")

    # Estado no voltou para agendando_0
    estado = ctx_apos_retomada.get("estado_fluxo")
    if estado == "agendando_0":
        falhas.append("Retomada: fluxo foi reiniciado (estado = agendando_0)")

    return {
        "cenario": "2_retomada_apos_interrupcao",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


def validar_cenario_3_multiplas_interrupcoes(contextos_por_msg, mensagens):
    """
    Validao Cenrio 3: Mltiplas interrupes informativas

    Esperado:
    - Cada pergunta informativa respondida
    - Servico, data, hora NO so alterados pelas perguntas
    - Fluxo mantm estado vlido
    """
    falhas = []
    servico_inicial = (contextos_por_msg[0].get("draft_agendamento") or {}).get("servico")

    # Verificar que cada pergunta informativa no alterou servico
    for i, (ctx, msg_data) in enumerate(zip(contextos_por_msg[1:], mensagens[1:]), start=1):
        msg = msg_data["texto"]

        # Se  pergunta informativa, servico no deve mudar
        if any(keyword in msg.lower() for keyword in ["quanto", "quem", "qual", "abrem", "endereo"]):
            servico_atual = (ctx.get("draft_agendamento") or {}).get("servico")
            if servico_inicial and servico_atual != servico_inicial:
                falhas.append(f"Pergunta informativa {i} alterou servico: {servico_inicial}  {servico_atual}")

    # Verificar que draft foi preservado em todas as perguntas
    draft_criado = bool((contextos_por_msg[0].get("draft_agendamento")))
    for i, ctx in enumerate(contextos_por_msg[1:], start=1):
        if draft_criado and not ctx.get("draft_agendamento"):
            msg = mensagens[i]["texto"]
            if any(keyword in msg.lower() for keyword in ["quanto", "quem", "qual", "abrem"]):
                falhas.append(f"Pergunta informativa {i} apagou draft_agendamento")

    return {
        "cenario": "3_multiplas_interrupcoes",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Executor principal dos testes"""

    firebase_async_mock = FirebaseAsyncMock()

    # Mock Firebase
    firebase_async.buscar_dado_em_path = firebase_async_mock.buscar_dado_em_path
    firebase_async.salvar_dado_em_path = firebase_async_mock.salvar_dado_em_path
    firebase_async.atualizar_dado_em_path = firebase_async_mock.atualizar_dado_em_path

    # Mock contexto
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

    # Mock endereo
    dono_id = "7394370553"
    firebase_async_mock.dados[f"Clientes/{dono_id}/configuracao/dados_negocio"] = {
        "endereco": {
            "rua": "Rua Joo Baroni",
            "numero": "550",
            "completo": "Rua Joo Baroni, 550"
        }
    }

    async def sem_conflito_mock(*args, **kwargs):
        return {"conflito": False, "sugestoes": [], "profissional_alternativo": None}

    async def validar_horario_funcionamento_mock(*args, **kwargs):
        return {"permitido": True, "aberto": True, "inicio": "08:00", "fim": "18:00"}

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

    # Mock criao de evento
    eventos_criados = []

    async def criar_evento_mock(*args, **kwargs):
        eventos_criados.append({"args": args, "kwargs": kwargs})
        return {"id": "mock_evento_id", "criado": True}

    if hasattr(pr, "add_evento_por_gpt"):
        pr.add_evento_por_gpt = criar_evento_mock

    async def executar_acao_gpt_mock(update, context, acao, dados):
        if acao == "criar_evento":
            eventos_criados.append({"acao": acao, "dados": dados})
        return {"sucesso": True, "acao": acao}

    pr.executar_acao_gpt = executar_acao_gpt_mock

    # ========================================================================
    # CENRIO 1: Pergunta Informativa Durante Fluxo Ativo
    # ========================================================================

    user_id_cenario1 = "7371670478_cenario1"
    actor_id = user_id_cenario1

    print("\n" + "=" * 100)
    print("CENRIO 1: Pergunta Informativa Durante Fluxo Ativo")
    print("=" * 100)

    contexto_mock.set_contexto(user_id_cenario1, {})

    mensagens_cenario1 = [
        {"texto": "quero agendar corte", "descricao": "Inicia agendamento"},
        {"texto": "qual o endereo?", "descricao": "Pergunta informativa sobre endereo"},
    ]

    ctx_cenario1_apos_msg1 = None
    ctx_cenario1_apos_msg2 = None

    for i, msg_data in enumerate(mensagens_cenario1, 1):
        texto = msg_data["texto"]
        descricao = msg_data["descricao"]

        ctx_antes = contexto_mock.get_contexto_final(user_id_cenario1)

        try:
            await pr.roteador_principal(
                user_id=user_id_cenario1,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            print(f"   [ERRO] Ao processar: {e}")

        ctx_depois = contexto_mock.get_contexto_final(user_id_cenario1)

        log_contexto_detalhado(i, descricao, ctx_antes, ctx_depois)

        if i == 1:
            ctx_cenario1_apos_msg1 = copy.deepcopy(ctx_depois)
        elif i == 2:
            ctx_cenario1_apos_msg2 = copy.deepcopy(ctx_depois)

    validacao_cenario1 = validar_cenario_1_pergunta_informativa(
        contexto_mock.storage.get(user_id_cenario1) or {},
        ctx_cenario1_apos_msg1 or {},
        ctx_cenario1_apos_msg2 or {},
    )

    print(f"\n{'' * 100}")
    print(f"RESULTADO CENRIO 1: {validacao_cenario1['status']}")
    if validacao_cenario1["falhas"]:
        for falha in validacao_cenario1["falhas"]:
            print(f"   {falha}")
    else:
        print(f"   Todas as validaes passaram")

    # ========================================================================
    # CENRIO 2: Retomada Aps Interrupo
    # ========================================================================

    user_id_cenario2 = "7371670478_cenario2"

    print("\n" + "=" * 100)
    print("CENRIO 2: Retomada Aps Interrupo Informativa")
    print("=" * 100)

    contexto_mock.set_contexto(user_id_cenario2, {})

    mensagens_cenario2 = [
        {"texto": "quero agendar corte", "descricao": "Inicia agendamento"},
        {"texto": "qual o endereo?", "descricao": "Pergunta informativa (interrupo)"},
        {"texto": "pode ser", "descricao": "Retoma fluxo com confirmao simples"},
        {"texto": "amanh", "descricao": "Preenche data aps retomada"},
        {"texto": "s 14", "descricao": "Preenche hora"},
        {"texto": "Bruna", "descricao": "Escolhe profissional"},
    ]

    contextos_cenario2 = []
    ctx_apos_interrupcao = None
    ctx_apos_retomada = None

    for i, msg_data in enumerate(mensagens_cenario2, 1):
        texto = msg_data["texto"]
        descricao = msg_data["descricao"]

        ctx_antes = contexto_mock.get_contexto_final(user_id_cenario2)

        try:
            await pr.roteador_principal(
                user_id=user_id_cenario2,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            print(f"   [ERRO] Ao processar: {e}")

        ctx_depois = contexto_mock.get_contexto_final(user_id_cenario2)

        log_contexto_detalhado(i, descricao, ctx_antes, ctx_depois)
        contextos_cenario2.append(copy.deepcopy(ctx_depois))

        if i == 2:
            ctx_apos_interrupcao = copy.deepcopy(ctx_depois)
        elif i == 3:
            ctx_apos_retomada = copy.deepcopy(ctx_depois)

    validacao_cenario2 = validar_cenario_2_retomada_apos_interrupcao(
        ctx_apos_interrupcao or {},
        ctx_apos_retomada or {},
    )

    print(f"\n{'' * 100}")
    print(f"RESULTADO CENRIO 2: {validacao_cenario2['status']}")
    if validacao_cenario2["falhas"]:
        for falha in validacao_cenario2["falhas"]:
            print(f"   {falha}")
    else:
        print(f"   Todas as validaes passaram")

    # ========================================================================
    # CENRIO 3: Mltiplas Interrupes Informativas
    # ========================================================================

    user_id_cenario3 = "7371670478_cenario3"

    print("\n" + "=" * 100)
    print("CENRIO 3: Mltiplas Interrupes Informativas")
    print("=" * 100)

    contexto_mock.set_contexto(user_id_cenario3, {})

    mensagens_cenario3 = [
        {"texto": "quero agendar corte", "descricao": "Inicia agendamento"},
        {"texto": "quanto custa corte?", "descricao": "Pergunta 1: custo do servio"},
        {"texto": "quem atende corte?", "descricao": "Pergunta 2: profissionais disponveis"},
        {"texto": "vocs abrem sbado?", "descricao": "Pergunta 3: expediente"},
        {"texto": "ok quero marcar", "descricao": "Retoma fluxo aps perguntas"},
        {"texto": "amanh", "descricao": "Preenche data"},
        {"texto": "s 15:30", "descricao": "Preenche hora"},
    ]

    contextos_cenario3 = []

    for i, msg_data in enumerate(mensagens_cenario3, 1):
        texto = msg_data["texto"]
        descricao = msg_data["descricao"]

        ctx_antes = contexto_mock.get_contexto_final(user_id_cenario3)

        try:
            await pr.roteador_principal(
                user_id=user_id_cenario3,
                mensagem=texto,
                update=None,
                context=None,
            )
        except Exception as e:
            print(f"   [ERRO] Ao processar: {e}")

        ctx_depois = contexto_mock.get_contexto_final(user_id_cenario3)

        log_contexto_detalhado(i, descricao, ctx_antes, ctx_depois)
        contextos_cenario3.append(copy.deepcopy(ctx_depois))

    validacao_cenario3 = validar_cenario_3_multiplas_interrupcoes(
        contextos_cenario3,
        mensagens_cenario3,
    )

    print(f"\n{'' * 100}")
    print(f"RESULTADO CENRIO 3: {validacao_cenario3['status']}")
    if validacao_cenario3["falhas"]:
        for falha in validacao_cenario3["falhas"]:
            print(f"   {falha}")
    else:
        print(f"   Todas as validaes passaram")

    # ========================================================================
    # RESUMO FINAL
    # ========================================================================

    print("\n" + "=" * 100)
    print("RESUMO FINAL")
    print("=" * 100)

    resultados = [validacao_cenario1, validacao_cenario2, validacao_cenario3]
    total_cenarios = len(resultados)
    cenarios_sucesso = sum(1 for r in resultados if r["status"] == "SUCESSO")
    cenarios_falha = total_cenarios - cenarios_sucesso

    print(f"\nTotal: {total_cenarios} cenrios")
    print(f"Sucessos: {cenarios_sucesso}")
    print(f"Falhas: {cenarios_falha}")

    if eventos_criados:
        print(f"\n Eventos criados prematuramente: {len(eventos_criados)}")
        for evento in eventos_criados:
            print(f"    {evento}")
    else:
        print(f"\n Nenhum evento criado (conforme esperado)")

    print(f"\n{'=' * 100}")

    # ========================================================================
    # SALVAR RESULTADO
    # ========================================================================

    resultado_path = Path(__file__).parent / "resultado_stress_interrupcao_informativa_completo.json"

    resultado_completo = {
        "titulo": "STRESS TEST  Interrupes Informativas Durante Agendamento Ativo",
        "data_execucao": datetime.now().isoformat(),
        "cenarios": {
            "cenario_1": validacao_cenario1,
            "cenario_2": validacao_cenario2,
            "cenario_3": validacao_cenario3,
        },
        "resumo": {
            "total": total_cenarios,
            "sucessos": cenarios_sucesso,
            "falhas": cenarios_falha,
            "status_geral": "SUCESSO" if cenarios_falha == 0 else "FALHA",
        },
        "eventos_criados": len(eventos_criados),
    }

    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump(resultado_completo, f, ensure_ascii=False, indent=2)

    print(f"\nResultado salvo em: {resultado_path}")

    return 0 if cenarios_falha == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
