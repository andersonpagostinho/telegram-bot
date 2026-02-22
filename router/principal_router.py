# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

import unidecode


async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    # ✅ Verificar consulta informativa ANTES de tudo
    from services.informacao_service import responder_consulta_informativa

    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
    if resposta_informativa:
        print("🔍 Consulta informativa detectada. Respondendo diretamente.")
        if context is not None:
            await context.bot.send_message(
                chat_id=user_id,
                text=resposta_informativa,
                parse_mode="Markdown"
            )
        return resposta_informativa

    # 🔐 pega sempre o dono deste usuário (modelo 1 número = 1 negócio)
    dono_id = await obter_id_dono(user_id)

    # 🔒 MODO SEGURO helpers (use SEMPRE "mensagem")
    texto_usuario = (mensagem or "").strip().lower()

    def eh_confirmacao(txt: str) -> bool:
        gatilhos = ["confirmar", "confirmo", "confirmado", "pode agendar", "pode marcar", "agende", "marque"]
        return any(g in txt for g in gatilhos)

    def eh_consulta(txt: str) -> bool:
        consultas = [
            "como está", "como esta", "agenda",
            "disponível", "disponivel",
            "tem horário", "tem horario",
            "livre", "ocupado", "ocupada",
            "consulta", "consultar"
        ]
        return any(c in txt for c in consultas)

    # ✅ PATCH 2: consulta → agendamento (criar pendência quando usuário pedir "pode agendar")
    ctx = await carregar_contexto_temporario(user_id) or {}

    gatilho_agendar = any(x in texto_usuario for x in ["pode agendar", "pode marcar", "agende", "marque"])
    if gatilho_agendar:
        data_hora = ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")

        if data_hora and prof:
            ctx["pendente_confirmacao"] = {
                "acao": "criar_evento",
                "dados": {"data_hora": data_hora, "profissional": prof},
                "criado_em": "now",
            }
            await atualizar_contexto(user_id, ctx)

            # força cair no bloco de confirmação/continuidade
            texto_usuario = "confirmar"

    # ✅ MODO SEGURO: se existe ação pendente e o usuário confirmou, executa SEM chamar GPT
    pend = ctx.get("pendente_confirmacao")

    if pend and pend.get("acao") in ("criar_evento", "cancelar_evento") and eh_confirmacao(texto_usuario):
        acao_p = pend["acao"]
        dados_p = pend.get("dados", {}) or {}

        # ============================================================
        # ✅ CONTINUIDADE: completar dados com o contexto salvo
        # (principalmente: servico)
        ctx_atual = await carregar_contexto_temporario(user_id) or {}
        servico = dados_p.get("servico") or ctx_atual.get("servico")
        prof = dados_p.get("profissional") or ctx_atual.get("profissional_escolhido")
        data_hora = dados_p.get("data_hora") or ctx_atual.get("data_hora")

        # Se a ação é criar_evento e falta serviço, não executa ainda:
        if acao_p == "criar_evento" and not servico:
            dono_id = await obter_id_dono(user_id)
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

            servs = []
            for p in profs_dict.values():
                if (p.get("nome", "").strip().lower() == (prof or "").strip().lower()):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join(servs)

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Perfeito. Qual serviço você quer agendar com "
                        f"{prof or 'a profissional'} às {data_hora or 'nesse horário'}?"
                        f"{sugestao}"
                    )
                )

            # mantém pendência (NÃO limpa), só marca estado
            ctx_atual["aguardando_servico"] = True
            await atualizar_contexto(user_id, ctx_atual)
            return {"acao": None, "handled": True}

        # Se já tem serviço (ou não é criar_evento), pode executar:
        # completa dados_p antes de passar ao executor
        if servico and "servico" not in dados_p:
            dados_p["servico"] = servico
        if prof and "profissional" not in dados_p:
            dados_p["profissional"] = prof
        if data_hora and "data_hora" not in dados_p:
            dados_p["data_hora"] = data_hora
        # ============================================================

        # ✅ Agora sim: limpa pendência ANTES de executar (evita dupla execução)
        ctx["pendente_confirmacao"] = None
        await atualizar_contexto(user_id, ctx)

        print(f"✅ CONFIRMAÇÃO detectada. Executando pendência: {acao_p}", flush=True)
        await executar_acao_gpt(update, context, acao_p, dados_p)
        return {"acao": acao_p, "handled": True}

    # ============================================================
    # ✅ NOVO: atalho determinístico quando estamos aguardando o SERVIÇO
    # Evita chamar GPT e evita voltar para escolha de profissional

    if ctx_atual.get("aguardando_servico"):
        # Recupera o mínimo necessário para agendar
        prof = ctx_atual.get("profissional_escolhido") or (ctx_atual.get("ultima_consulta") or {}).get("profissional")
        data_hora = ctx_atual.get("data_hora") or (ctx_atual.get("ultima_consulta") or {}).get("data_hora")

        # Carrega serviços (preferência: serviços do profissional escolhido)
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

        servs_prof = []
        servs_todos = set()

        for p in profs_dict.values():
            servs = p.get("servicos") or []
            for s in servs:
                if s:
                    servs_todos.add(str(s).strip())
            if prof and (p.get("nome", "").strip().lower() == str(prof).strip().lower()):
                servs_prof = [str(s).strip() for s in servs if s]
                break

        # Lista válida para validação do texto do usuário
        candidatos = servs_prof or list(servs_todos)

        # Normaliza para match (aceita "corte", "Corte", etc.)
        txt_norm = unidecode.unidecode((texto_usuario or "").lower().strip())
        mapa_norm = {unidecode.unidecode(str(s).lower().strip()): str(s).strip() for s in candidatos}

        servico_escolhido = mapa_norm.get(txt_norm)

        if not servico_escolhido:
            # Se não bateu exato, tenta substring (ex: "quero corte")
            for k_norm, original in mapa_norm.items():
                if k_norm and k_norm in txt_norm:
                    servico_escolhido = original
                    break

        if servico_escolhido and prof and data_hora:
            # Atualiza contexto e executa direto
            ctx_atual["servico"] = servico_escolhido
            ctx_atual["aguardando_servico"] = False

            # Se existe pendência, completa e limpa antes de executar
            pend2 = ctx_atual.get("pendente_confirmacao")
            if pend2 and pend2.get("acao") == "criar_evento":
                pend2_dados = pend2.get("dados", {}) or {}
                pend2_dados["servico"] = servico_escolhido
                pend2_dados["profissional"] = pend2_dados.get("profissional") or prof
                pend2_dados["data_hora"] = pend2_dados.get("data_hora") or data_hora
                ctx_atual["pendente_confirmacao"] = None

            await atualizar_contexto(user_id, ctx_atual)

            await executar_acao_gpt(
                update,
                context,
                "criar_evento",
                {"servico": servico_escolhido, "profissional": prof, "data_hora": data_hora},
            )
            return {"acao": "criar_evento", "handled": True}

        # Se não reconheceu o serviço, pede novamente sem envolver GPT
        if context is not None:
            sugestao = ""
            if candidatos:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join(sorted(set(candidatos)))
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Entendi. Qual serviço você deseja agendar?{sugestao}"
            )
        return {"acao": None, "handled": True}
    # ============================================================

    # ✅ FALLBACK determinístico: usuário respondeu o SERVIÇO mesmo sem flag 'aguardando_servico'
    
    prof = ctx_atual.get("profissional_escolhido") or (ctx_atual.get("ultima_consulta") or {}).get("profissional")
    data_hora = ctx_atual.get("data_hora") or (ctx_atual.get("ultima_consulta") or {}).get("data_hora")
    pend = ctx_atual.get("pendente_confirmacao") or {}
    ja_ha_confirmacao = (pend.get("acao") == "criar_evento")

    # Só tenta se já existe contexto mínimo e ainda não existe serviço salvo
    if prof and data_hora and not ctx_atual.get("servico"):
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

        # pega serviços do profissional escolhido (prioridade)
        servs_prof = []
        for p in profs_dict.values():
            if (p.get("nome", "").strip().lower() == str(prof).strip().lower()):
                servs_prof = [str(s).strip() for s in (p.get("servicos") or []) if s]
                break

        # se não achou, cai pro conjunto geral do salão
        if not servs_prof:
            servs_prof = sorted({str(s).strip() for p in profs_dict.values() for s in (p.get("servicos") or []) if s})

        txt_norm = unidecode.unidecode((texto_usuario or "").lower().strip())
        mapa_norm = {unidecode.unidecode(s.lower().strip()): s for s in servs_prof}

        servico_escolhido = mapa_norm.get(txt_norm)
        if not servico_escolhido:
            # substring: "quero corte", "pode ser corte", etc.
            for k_norm, original in mapa_norm.items():
                if k_norm and k_norm in txt_norm:
                    servico_escolhido = original
                    break

        if servico_escolhido:
            # mantém modo seguro: se ainda não houve confirmação, salva pendência e pede "confirmar"
            if not ja_ha_confirmacao and not eh_confirmacao(texto_usuario):
                ctx_atual["pendente_confirmacao"] = {
                    "acao": "criar_evento",
                    "dados": {"servico": servico_escolhido, "profissional": prof, "data_hora": data_hora},
                    "criado_em": "now",
                }
                ctx_atual["servico"] = servico_escolhido
                await atualizar_contexto(user_id, ctx_atual)

                if context is not None:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Perfeito: *{servico_escolhido}* com *{prof}* em *{data_hora}*.\n\n"
                            f"👉 Para confirmar, responda: *confirmar*"
                        ),
                        parse_mode="Markdown"
                    )
                return {"acao": None, "handled": True}

            # se já confirmou, executa direto
            ctx_atual["servico"] = servico_escolhido
            ctx_atual["aguardando_servico"] = False
            ctx_atual["pendente_confirmacao"] = None
            await atualizar_contexto(user_id, ctx_atual)

            await executar_acao_gpt(
                update,
                context,
                "criar_evento",
                {"servico": servico_escolhido, "profissional": prof, "data_hora": data_hora},
            )
            return {"acao": "criar_evento", "handled": True}

    # 🔄 Sessão ativa (ex: agendamento, tarefa etc.)
    sessao = await pegar_sessao(user_id)
    if sessao and sessao.get("estado"):
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

    # 🧠 Monta contexto pro GPT
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = {
        "user_id": user_id,
        "id_negocio": dono_id,
    }

    # 👉 busca profissionais do DONO, não do cliente
    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    # 🧠 Chama o GPT com o contexto de secretaria
    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 resposta_gpt retornada:", resposta_gpt)

    # cumprimentos especiais
    cumprimentos = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "eai", "tudo bem?"]
    if resposta_gpt.get("acao") == "buscar_tarefas_do_usuario" and mensagem.lower().strip() in cumprimentos:
        resposta_gpt = {"resposta": "Olá! Como posso ajudar?", "acao": None, "dados": {}}

    # segurança
    if not resposta_gpt or not isinstance(resposta_gpt, dict):
        print("⚠️ Resposta do GPT inválida ou vazia:", resposta_gpt)
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text="❌ Ocorreu um erro ao interpretar sua mensagem.")
        return

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {})

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
            # 🚫 TRAVA GLOBAL (MODO SEGURO)
            if acao in ("criar_evento", "cancelar_evento") and not eh_confirmacao(texto_usuario):
                if "consultar" in texto_usuario or eh_consulta(texto_usuario):
                    print(f"ℹ️ Rebaixado para consulta (sem executar '{acao}') | texto='{texto_usuario}'", flush=True)
                    acao = None
                    dados = {}
                else:
                    # ✅ Salva pendência para próxima mensagem "confirmar"
                    ctx = await carregar_contexto_temporario(user_id) or {}
                    ctx["pendente_confirmacao"] = {"acao": acao, "dados": dados, "criado_em": "now"}
                    await atualizar_contexto(user_id, ctx)

                    print(f"🛑 BLOQUEADO: '{acao}' sem confirmação explícita | pendência salva", flush=True)
                    if context is not None:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=(
                                "Por segurança eu não executo ações sem confirmação.\n\n"
                                "👉 Para confirmar, responda: confirmar\n"
                                "Se era só consulta, responda: consultar"
                            )
                        )
                    return

            if acao:
                handled = await executar_acao_gpt(update, context, acao, dados)

                # ✅ Patch crítico: criar_evento responde no handler
                if acao == "criar_evento":
                    return {"acao": "criar_evento", "handled": True}

    # ✅ Só envia resposta do GPT se NÃO houve ação (ou se ação foi rebaixada)
    if (not acao) and resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text=resposta_texto, parse_mode="Markdown")
        return {"resposta": resposta_texto}

    if acao:
        return {"acao": acao, "handled": bool(handled)}

    return {"resposta": "❌ Não consegui interpretar sua mensagem."}