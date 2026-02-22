# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

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
    ctx["intencao_agendar"] = True


def normalizar(texto: str) -> str:
    return unidecode((texto or "").strip().lower())


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
    # ✅ NOVO: Estado único do fluxo (estado_fluxo)
    # =========================================================
    texto_usuario = (mensagem or "").strip()
    texto_lower = texto_usuario.lower().strip()

    ctx = await carregar_contexto_temporario(user_id) or {}
    estado_fluxo = (ctx.get("estado_fluxo") or "idle").strip().lower()
    draft = ctx.get("draft_agendamento") or {}
    print(f"🧭 [estado_fluxo] user={user_id} estado_fluxo_raw={ctx.get('estado_fluxo')} estado_fluxo_norm={estado_fluxo} draft={ctx.get('draft_agendamento')}", flush=True)

    # 🚀 AUTO-EXECUÇÃO (sem GPT) — somente com intenção explícita
    servico = ctx.get("servico")
    data_hora = ctx.get("data_hora")
    prof = ctx.get("profissional_escolhido")
    intencao_agendar = bool(ctx.get("intencao_agendar"))

    if servico and data_hora and prof and intencao_agendar and estado_fluxo == "idle":
        print("🔥 AUTO-EXEC: contexto completo + intenção explícita, executando sem GPT", flush=True)

        ctx["estado_fluxo"] = "agendando"
        await atualizar_contexto(user_id, ctx)

        dados_exec = {"servico": servico, "profissional": prof, "data_hora": data_hora}
        await executar_acao_gpt(update, context, "criar_evento", dados_exec)

        # ✅ limpa slots para não re-executar em mensagens seguintes
        ctx = await carregar_contexto_temporario(user_id) or {}
        ctx["estado_fluxo"] = "idle"
        ctx["draft_agendamento"] = None
        ctx["intencao_agendar"] = False
        ctx["servico"] = None
        ctx["data_hora"] = None
        ctx["profissional_escolhido"] = None
        ctx["ultima_consulta"] = None
        await atualizar_contexto(user_id, ctx)

        return {"acao": "criar_evento", "handled": True}

    # 0) Se o usuário está EM "aguardando_servico", então essa mensagem deve ser interpretada como serviço
    if estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        # precisamos: profissional + data_hora no draft
        prof = draft.get("profissional") or ctx.get("profissional_escolhido")
        data_hora = draft.get("data_hora") or ctx.get("data_hora")

        if not prof or not data_hora:
            ctx["estado_fluxo"] = "idle"
            ctx["draft_agendamento"] = None
            await atualizar_contexto(user_id, ctx)
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Perdi o contexto do agendamento. Pode me dizer novamente o dia/hora e profissional?")
            return {"acao": None, "handled": True}

        # buscar serviços do profissional para validar
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        servs = []
        for p in profs_dict.values():
            if normalizar(p.get("nome", "")) == normalizar(prof):
                servs = p.get("servicos") or []
                break

        texto_usuario = (mensagem or "").strip()
        servico_detectado = extrair_servico_do_texto(texto_usuario, servs)

        if not servico_detectado:
            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Ok. Para agendar com *{prof or 'a profissional'}* às *{data_hora or 'nesse horário'}*, "
                        f"me diga qual serviço você quer.{sugestao}"
                    ),
                    parse_mode="Markdown",
                )
            return {"acao": None, "handled": True}

        # completou serviço -> executar agendamento sem GPT
        draft["servico"] = servico_detectado
        draft["profissional"] = prof
        draft["data_hora"] = data_hora

        # marca estado e salva
        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = draft
        ctx["servico"] = servico_detectado  # opcional: ajuda relatórios/continuidade
        await atualizar_contexto(user_id, ctx)

        dados_exec = {
            "servico": draft["servico"],
            "profissional": draft["profissional"],
            "data_hora": draft["data_hora"],
        }

        print("✅ [estado_fluxo] Executando criar_evento com draft_agendamento:", dados_exec, flush=True)
        await executar_acao_gpt(update, context, "criar_evento", dados_exec)

        # limpa draft e volta pra idle (mantém histórico se você quiser no futuro)
        ctx = await carregar_contexto_temporario(user_id) or {}
        ctx["estado_fluxo"] = "idle"
        ctx["draft_agendamento"] = None
        await atualizar_contexto(user_id, ctx)

        return {"acao": "criar_evento", "handled": True}

    # 2) Se o usuário disser "pode agendar então", isso é decisão final.
    #    A regra é: se já tenho data_hora + profissional, eu vou para:
    #    - se já tenho servico: agendo agora
    #    - se não: peço só o serviço (sem voltar pro zero)
    if eh_gatilho_agendar(texto_lower):
        print("🟦 ENTROU NO gatilho_agendar", flush=True)
        print("🟩 ENTROU NO aguardando_servico", flush=True)
        data_hora = ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = ctx.get("servico")

        if data_hora and prof:
            # monta draft
            draft = {
                "data_hora": data_hora,
                "profissional": prof,
                "servico": servico,
            }
            ctx["draft_agendamento"] = draft

            if servico:
                # já tem tudo -> executa agora
                ctx["estado_fluxo"] = "agendando"
                await atualizar_contexto(user_id, ctx)

                dados_exec = {"servico": servico, "profissional": prof, "data_hora": data_hora}
                print("✅ [estado_fluxo] Gatilho agendar com contexto completo:", dados_exec, flush=True)
                await executar_acao_gpt(update, context, "criar_evento", dados_exec)

                ctx = await carregar_contexto_temporario(user_id) or {}
                ctx["estado_fluxo"] = "idle"
                ctx["draft_agendamento"] = None
                await atualizar_contexto(user_id, ctx)

                return {"acao": "criar_evento", "handled": True}

            # falta serviço -> pedir só serviço e mudar estado
            ctx["estado_fluxo"] = "aguardando_servico"
            await atualizar_contexto(user_id, ctx)

            # lista serviços do profissional (para não ficar “bot burro”)
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            # ✅ salva estado + draft (uma vez só)
            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
            }
            await atualizar_contexto(user_id, ctx)

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Perfeito. Qual serviço você quer agendar com *{prof}* às *{data_hora}*?"
                        f"{sugestao}"
                    ),
                    parse_mode="Markdown",
                )

            return {"acao": None, "handled": True}

        # se não tem data_hora/prof, cai no GPT (porque falta base)
        # (continua a execução normal)

    # 1) Se a mensagem for consulta, marcar estado e GARANTIR que não agenda
    if eh_consulta(texto_lower):
        # salva um "marco" de consulta para o próximo "pode agendar"
        data_hora = ctx.get("data_hora")
        prof = ctx.get("profissional_escolhido")

        ctx["estado_fluxo"] = "consultando"
        if data_hora or prof:
            ctx["ultima_consulta"] = {
                "data_hora": data_hora,
                "profissional": prof,
            }
        await atualizar_contexto(user_id, ctx)

        # segue para GPT responder a consulta (mas vamos bloquear ações mutáveis depois)
        # (continua a execução normal)

    

    # =========================================================
    # 3) Chamada normal ao GPT (com contexto do dono)
    # =========================================================
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = {
        "user_id": user_id,
        "id_negocio": dono_id,
    }

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 resposta_gpt retornada:", resposta_gpt)

    # cumprimentos especiais
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
    if eh_consulta(texto_lower) and acao in ("criar_evento", "cancelar_evento"):
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
            # ✅ Agora sem “segunda confirmação”: executa
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