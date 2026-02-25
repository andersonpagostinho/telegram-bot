# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from datetime import datetime

import re
from unidecode import unidecode


# ----------------------------
# Helpers de NLP simples
# ----------------------------

def eh_consulta(txt: str) -> bool:
    """
    Heurística: detectar mensagens de consulta de agenda/disponibilidade.
    Consulta NUNCA deve agendar.
    """
    t = (txt or "").strip().lower()
    consultas = [
        "como está", "como esta", "agenda",
        "disponível", "disponivel",
        "tem horário", "tem horario",
        "livre", "ocupado", "ocupada",
        "consulta", "consultar",
        "disponibilidade",
    ]
    return any(c in t for c in consultas)


def eh_gatilho_agendar(txt: str) -> bool:
    """
    Gatilho explícito de agendar (decisão final do usuário).
    """
    t = (txt or "").strip().lower()
    gatilhos = ["pode agendar", "pode marcar", "agende", "marque"]
    return any(g in t for g in gatilhos)


def normalizar(texto: str) -> str:
    return unidecode((texto or "").strip().lower())

def formatar_data_hora_br(dt_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_iso)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(dt_iso)

def extrair_servico_do_texto(texto_usuario: str, servicos_disponiveis: list) -> str | None:
    """
    Tenta mapear o texto do usuário para um serviço existente do profissional.
    - match por inclusão normalizada (robusto para "corte", "escova", etc.)
    """
    if not servicos_disponiveis:
        return None

    txt = normalizar(texto_usuario)
    if not txt:
        return None

    # match direto: "corte" dentro da mensagem
    for s in servicos_disponiveis:
        s_norm = normalizar(str(s))
        if s_norm and s_norm in txt:
            return str(s).strip()

    # match aproximado: mensagem curta igual a serviço
    if len(txt.split()) <= 2:
        for s in servicos_disponiveis:
            if normalizar(str(s)) == txt:
                return str(s).strip()

    return None


# ----------------------------
# Router principal
# ----------------------------

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    # ✅ 1) consulta informativa antes de tudo
    from services.informacao_service import responder_consulta_informativa

    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
    if resposta_informativa:
        print("🔍 Consulta informativa detectada. Respondendo diretamente.")
        if context is not None:
            await context.bot.send_message(
                chat_id=user_id,
                text=resposta_informativa,
                parse_mode="Markdown",
            )
        return resposta_informativa

    # 🔐 dono do negócio
    dono_id = await obter_id_dono(user_id)

    # 🔄 sessão ativa (fluxos do seu gpt_service)
    sessao = await pegar_sessao(user_id)
    if sessao and sessao.get("estado"):
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

    # =========================================================
    # ✅ Estado único do fluxo (estado_fluxo)
    # =========================================================
    texto_usuario = (mensagem or "").strip()
    texto_lower = texto_usuario.lower().strip()

    ctx = await carregar_contexto_temporario(user_id) or {}
    estado_fluxo = (ctx.get("estado_fluxo") or "idle").strip().lower()
    draft = ctx.get("draft_agendamento") or {}

    # =========================================================
    # ✅ CONFIRMAÇÃO NO MODO "consultando" -> vira coleta de serviço
    # =========================================================
    async def eh_confirmacao(txt: str) -> bool:
        t = (txt or "").strip().lower()
        gatilhos = [
            "confirmar", "confirma", "pode agendar", "pode marcar", "agende", "marque",
            "fechar", "ok", "confirmado",
            # ✅ faltavam estes (seu caso: "sim por favor")
            "sim", "sim por favor", "pode", "pode ser", "pode sim"
        ]
        return any(g in t for g in gatilhos)

        if estado_fluxo == "consultando" and eh_confirmacao(texto_lower):
            # base vem do contexto salvo (consulta anterior)
            prof = ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
            data_hora = ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")

            if prof and data_hora:
                # entra no fluxo determinístico (sem GPT)
                ctx["estado_fluxo"] = "aguardando_servico"
                ctx["draft_agendamento"] = {
                    "profissional": prof,
                    "data_hora": data_hora,
                    "servico": None,
                }
                await atualizar_contexto(user_id, ctx)

                data_hora_fmt = formatar_data_hora_br(data_hora)  # você já criou isso
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Perfeito — com *{prof}* em *{data_hora_fmt}*. Qual serviço vai ser?",
                    parse_mode="Markdown",
                )
                return {"acao": None, "handled": True}

    print(
        f"🧭 [estado_fluxo] user={user_id} "
        f"estado_fluxo_raw={ctx.get('estado_fluxo')} "
        f"estado_fluxo_norm={estado_fluxo} "
        f"draft={ctx.get('draft_agendamento')}",
        flush=True,
    )

    # ---------------------------------------------------------
    # 0) Se está aguardando_servico, essa mensagem É o serviço.
    # ---------------------------------------------------------
    if estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        prof = draft.get("profissional") or ctx.get("profissional_escolhido")
        data_hora = draft.get("data_hora") or ctx.get("data_hora")

        if not prof or not data_hora:
            ctx["estado_fluxo"] = "idle"
            ctx["draft_agendamento"] = None
            await atualizar_contexto(user_id, ctx)
            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Perdi o contexto do agendamento. Pode me dizer novamente o dia/hora e profissional?",
                )
            return {"acao": None, "handled": True}

        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        servs = []
        for p in profs_dict.values():
            if normalizar(p.get("nome", "")) == normalizar(prof):
                servs = p.get("servicos") or []
                break

        servico_detectado = extrair_servico_do_texto(texto_usuario, servs)

        if not servico_detectado:
            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Ok. Para agendar com *{prof}* às *{data_hora}*, "
                        f"me diga qual serviço você quer.{sugestao}"
                    ),
                    parse_mode="Markdown",
                )
            return {"acao": None, "handled": True}

        # executa sem GPT
        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico_detectado,
        }
        ctx["servico"] = servico_detectado
        await atualizar_contexto(user_id, ctx)

        dados_exec = {"servico": servico_detectado, "profissional": prof, "data_hora": data_hora}
        print("✅ [estado_fluxo] Executando criar_evento com draft_agendamento:", dados_exec, flush=True)
        dados_exec["origem"] = "auto"

        # volta para idle
        ctx = await carregar_contexto_temporario(user_id) or {}
        ctx["estado_fluxo"] = "idle"
        ctx["draft_agendamento"] = None
        await atualizar_contexto(user_id, ctx)

        return {"acao": "criar_evento", "handled": True}

    # ---------------------------------------------------------
    # 0.1) FALLBACK forte:
    # Se por qualquer motivo estado_fluxo ficou "consultando",
    # mas o usuário respondeu um serviço curto e existe ultima_consulta,
    # tratamos como serviço (não volta pro GPT).
    # ---------------------------------------------------------
    if estado_fluxo in ("consultando", "idle"):
        ultima = ctx.get("ultima_consulta") or {}
        prof_u = (ctx.get("profissional_escolhido") or ultima.get("profissional"))
        data_u = (ctx.get("data_hora") or ultima.get("data_hora"))
        if prof_u and data_u and len(normalizar(texto_usuario).split()) <= 3:
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof_u):
                    servs = p.get("servicos") or []
                    break

            servico_detectado = extrair_servico_do_texto(texto_usuario, servs)
            if servico_detectado:
                print("🟨 [fallback] Serviço detectado após consulta. Executando agendamento.", flush=True)

                ctx["estado_fluxo"] = "agendando"
                ctx["draft_agendamento"] = {
                    "profissional": prof_u,
                    "data_hora": data_u,
                    "servico": servico_detectado,
                }
                ctx["servico"] = servico_detectado
                await atualizar_contexto(user_id, ctx)

                dados_exec = {
                    "servico": servico_detectado,
                    "profissional": prof_u,
                    "data_hora": data_u,
                    "origem": "auto",
                    "texto_usuario": "confirmar",
                }
                await executar_acao_gpt(update, context, "criar_evento", dados_exec)

                ctx = await carregar_contexto_temporario(user_id) or {}
                ctx["estado_fluxo"] = "idle"
                ctx["draft_agendamento"] = None
                await atualizar_contexto(user_id, ctx)

                return {"acao": "criar_evento", "handled": True}

    # ---------------------------------------------------------
    # 1) Se a mensagem for consulta, marcar estado (sem sobrescrever subfluxos)
    # ---------------------------------------------------------
    if eh_consulta(texto_lower) and estado_fluxo == "idle":
        data_hora = ctx.get("data_hora")
        prof = ctx.get("profissional_escolhido")

        ctx["estado_fluxo"] = "consultando"
        if data_hora or prof:
            ctx["ultima_consulta"] = {"data_hora": data_hora, "profissional": prof}
        await atualizar_contexto(user_id, ctx)
        # segue para GPT responder a consulta (mas bloquearemos ações mutáveis depois)

    # ---------------------------------------------------------
    # 2) "pode agendar" = decisão final (consulta -> agendamento)
    # ---------------------------------------------------------
    if eh_gatilho_agendar(texto_lower):
        data_hora = ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = ctx.get("servico")

        if data_hora and prof:
            # já tem serviço -> executa já
            if servico:
                ctx["estado_fluxo"] = "agendando"
                await atualizar_contexto(user_id, ctx)

                dados_exec = {
                    "servico": servico,
                    "profissional": prof,
                    "data_hora": data_hora,
                    "origem": "auto",
                    "texto_usuario": "confirmar",
                }
                print("✅ [estado_fluxo] Gatilho agendar com contexto completo:", dados_exec, flush=True)
                await executar_acao_gpt(update, context, "criar_evento", dados_exec)

                ctx = await carregar_contexto_temporario(user_id) or {}
                ctx["estado_fluxo"] = "idle"
                ctx["draft_agendamento"] = None
                await atualizar_contexto(user_id, ctx)
                return {"acao": "criar_evento", "handled": True}

            # falta serviço -> pedir só serviço e entrar em aguardando_servico
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
            }
            await atualizar_contexto(user_id, ctx)

            data_hora_fmt = formatar_data_hora_br(data_hora) if data_hora else "esse horário"

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(f"Perfeito — com *{prof}* em *{data_hora_fmt}*. Qual serviço vai ser?{sugestao}"),
                    parse_mode="Markdown",
                )

            return {"acao": None, "handled": True}
        # se não tem base, cai no GPT (falta data_hora/prof)

    # =========================================================
    # 3) Chamada normal ao GPT (com contexto do dono)
    # =========================================================
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = {"user_id": user_id, "id_negocio": dono_id}

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 resposta_gpt retornada:", resposta_gpt)

    cumprimentos = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "eai", "tudo bem?"]
    if isinstance(resposta_gpt, dict) and resposta_gpt.get("acao") == "buscar_tarefas_do_usuario" and texto_lower in cumprimentos:
        resposta_gpt = {"resposta": "Olá! Como posso ajudar?", "acao": None, "dados": {}}

    # segurança
    if not resposta_gpt or not isinstance(resposta_gpt, dict):
        print("⚠️ Resposta do GPT inválida ou vazia:", resposta_gpt)
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text="❌ Ocorreu um erro ao interpretar sua mensagem.")
        return

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {}) or {}

    # ✅ REGRA DE OURO: se é CONSULTA, bloqueia ações mutáveis vindas do GPT
    # (usa também estado_fluxo consultando para ser mais robusto)
    if (eh_consulta(texto_lower) or estado_fluxo == "consultando") and acao in ("criar_evento", "cancelar_evento"):
        print(f"🛑 [estado_fluxo] Bloqueado '{acao}' pois mensagem é consulta: '{texto_lower}'", flush=True)
        acao = None
        dados = {}

    ACOES_SUPORTADAS = {
        "consultar_preco_servico",
        "criar_evento",
        "buscar_eventos_da_semana",
        "criar_tarefa",
        "remover_tarefa",
        "cancelar_evento",
        "listar_followups",
        "cadastrar_profissional",
        "aguardar_arquivo_importacao",
        "enviar_email",
        "organizar_semana",
        "buscar_tarefas_do_usuario",
        "buscar_emails",
        "verificar_pagamento",
        "verificar_acesso_modulo",
        "responder_audio",
        "criar_followup",
        "buscar_eventos_do_dia",
    }

    handled = False

    if acao:
        if acao not in ACOES_SUPORTADAS:
            print(f"⚠️ Ação '{acao}' não suportada. Ignorando...")
            acao = None
            dados = {}
        else:
            handled = await executar_acao_gpt(update, context, acao, dados)

            # criar_evento responde no handler (evita duplicar)
            if acao == "criar_evento":
                return {"acao": "criar_evento", "handled": True}

    # envia resposta do GPT se não houve ação
    if (not acao) and resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text=resposta_texto, parse_mode="Markdown")
        return {"resposta": resposta_texto}

    if acao:
        return {"acao": acao, "handled": bool(handled)}

    return {"resposta": "❌ Não consegui interpretar sua mensagem."}