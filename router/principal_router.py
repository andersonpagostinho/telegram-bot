# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


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
        gatilhos = ["confirmar", "confirmo", "confirmado"]
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

    # ✅ MODO SEGURO: se existe ação pendente e o usuário confirmou, executa SEM chamar GPT
    if eh_confirmacao(texto_usuario):
        ctx = await carregar_contexto_temporario(user_id) or {}
        pend = ctx.get("pendente_confirmacao")

        if pend and pend.get("acao") in ("criar_evento", "cancelar_evento"):
            acao_p = pend["acao"]
            dados_p = pend.get("dados", {})

            # limpa pendência ANTES de executar (evita dupla execução)
            ctx["pendente_confirmacao"] = None
            await atualizar_contexto(user_id, ctx)

            print(f"✅ CONFIRMAÇÃO detectada. Executando pendência: {acao_p}", flush=True)
            await executar_acao_gpt(update, context, acao_p, dados_p)
            return {"acao": acao_p, "handled": True}

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