# handlers/bot.py
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ApplicationHandlerStop,  # ✅ PTB v20+
)

from firebase_admin import firestore

# --- serviços/handlers próprios ---
from services.firebase_service_async import (
    buscar_cliente,
    salvar_cliente,
    verificar_firebase,
)
from services.event_service_async import cancelar_evento
from services.cadastro_inicial_service import (
    precisa_onboarding,
    mensagem_onboarding,
    processar_texto_cadastro,
)

from router.principal_router import roteador_principal

from handlers.task_handler import add_task, list_tasks, clear_tasks, list_tasks_by_priority
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, conectar_email
from handlers.event_handler import (
    add_agenda, list_events, confirmar_reuniao, confirmar_presenca,
    debug_eventos, cancelar_evento_cmd, enviar_agenda_excel
)
from handlers.importacao_handler import importar_profissionais_handler
from handlers.perfil_handler import (
    set_tipo_negocio, set_estilo_mensagem, set_nome_negocio, meu_estilo,
    set_email, meu_plano, meu_perfil, set_tipo_usuario, set_modo_uso,
    listar_profissionais
)
from handlers.voice_handler import handle_voice
from handlers.followup_handler import (
    criar_followup, listar_followups, verificar_avisos, configurar_avisos
)
from handlers.test_handler import testar_firebase, testar_avisos

from handlers.encaixe_handler import handle_pedido_encaixe
from handlers.reagendamento_handler import handle_resposta_reagendamento

# 👉 Se esses não existirem no seu repo, comente este import e os CommandHandler lá embaixo
from handlers.report_handler import (
    relatorio_diario,
    relatorio_semanal,
    enviar_relatorio_email,
)

logger = logging.getLogger(__name__)

# ============== HANDLERS DE MENSAGEM (ORDEM IMPORTA) ==============

async def _debug_primeiro_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler de diagnóstico (alta prioridade).
    Apenas registra no log que um texto passou pela pilha de handlers.
    Não responde ao usuário.
    """
    txt = (getattr(update.message, "text", "") or "").strip()
    uid = str(update.effective_user.id) if update.effective_user else "?"
    logger.info(f"🧭 [DEBUG-H0] Texto capturado: '{txt}' de {uid}")


async def tratar_mensagens_gerais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pipeline padrão:
    1) Atalho de cancelamento por número (estado em user_data)
    2) Fluxo de cadastro inicial (voz/texto: profissional/serviço/preço/duração)
    3) Roteador inteligente (IA)
    """
    print("📥 Entrou no tratar_mensagens_gerais()")

    # --- 1) atalho: concluir cancelamento pendente por número ---
    pend = context.user_data.get("cancelamento_pendente")
    msg_txt = (getattr(update.message, "text", "") or "").strip()

    if pend and msg_txt.isdigit():
        idx = int(msg_txt) - 1
        cands = pend.get("candidatos", [])
        user_id_cancel = str(pend.get("user_id") or update.effective_user.id)

        if 0 <= idx < len(cands):
            try:
                eid_escolhido = cands[idx]
                ok = await cancelar_evento(user_id_cancel, eid_escolhido)
                if ok:
                    await update.message.reply_text("✅ Cancelamento concluído. Horário liberado.")
                else:
                    await update.message.reply_text("❌ Não consegui cancelar. Pode tentar novamente?")
            finally:
                context.user_data.pop("cancelamento_pendente", None)
            # para aqui — não deixa outros handlers pegarem esta mesma msg
            raise ApplicationHandlerStop
        else:
            await update.message.reply_text("⚠️ Número inválido. Envie apenas o número da opção listada.")
            raise ApplicationHandlerStop
    # --- fim do atalho ---

    user_id = str(update.message.from_user.id)
    mensagem = msg_txt

    # --- 2) fluxo de configuração inicial (voz/texto) ---
    try:
        resposta_cfg = await processar_texto_cadastro(user_id, mensagem)
        if resposta_cfg:
            # Se o fluxo de cadastro entendeu e gerou resposta, envia e encerra
            await update.message.reply_text(resposta_cfg, parse_mode="Markdown")
            raise ApplicationHandlerStop
    except Exception as e:
        logger.warning(f"[config] Erro ao processar cadastro inicial: {e}")

    # --- 3) roteador inteligente (IA) ---
    try:
        resposta = await roteador_principal(user_id, mensagem, update, context)
        if resposta and isinstance(resposta, dict) and resposta.get("resposta"):
            await update.message.reply_text(resposta["resposta"], parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"❌ Erro no roteador_principal: {e}")
        await update.message.reply_text("⚠️ Tive um problema para processar sua solicitação agora. Pode repetir?")


# ============== COMANDOS ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)

    cliente_existente = await buscar_cliente(user_id)

    if cliente_existente:
        tipo_usuario = cliente_existente.get("tipo_usuario") or "cliente"
        id_negocio = cliente_existente.get("id_negocio") or user_id
    else:
        tipo_usuario = "dono"
        id_negocio = user_id

    modo_uso = "interno" if tipo_usuario == "dono" else "atendimento_cliente"

    dados = {
        "nome": f"{user.first_name} {user.last_name or ''}".strip(),
        "email": "",
        "pagamentoAtivo": True,
        "dataAssinatura": datetime.now().strftime("%Y-%m-%d"),
        "proximoPagamento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "planosAtivos": ["secretaria"],
        "tipo_usuario": tipo_usuario,
        "modo_uso": modo_uso,
        "id_negocio": id_negocio,
        "tipo_negocio": "",
        "estilo": ""
    }

    await salvar_cliente(user_id, dados)

    if tipo_usuario == "dono":
        mensagem = (
            f"👋 Olá, {user.first_name}! Detectei que você é o *dono* do negócio.\n\n"
            f"🎯 O modo *interno* já foi ativado automaticamente.\n"
            f"✅ Agora é só começar a usar! Você pode digitar /help para ver tudo que posso fazer.\n\n"
            f"✨ Dica: personalize como quiser com os comandos:\n"
            f"/tipo_negocio – ex: salão, clínica, etc.\n"
            f"/estilo – formal ou casual\n"
            f"/meu_email – para envio de mensagens\n"
            f"/profissional – para cadastrar sua equipe"
        )
    else:
        mensagem = (
            f"👋 Olá, {user.first_name}! Sou *NeoEve*, sua secretária virtual com inteligência contextual.\n\n"
            f"📌 Você foi conectado ao sistema de atendimento do negócio.\n"
            f"A qualquer momento, pode fazer perguntas como:\n"
            f"• “Tem horário para corte amanhã?”\n"
            f"• “Quem faz escova?”\n"
            f"• “Quais horários disponíveis hoje?”\n\n"
            f"😉 Se precisar de algo mais, estou aqui!"
        )

    # Onboarding (primeira configuração)
    try:
        if await precisa_onboarding(user_id):
            await update.message.reply_text(mensagem_onboarding(), parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"[start] Falha ao checar onboarding: {e}")

    await update.message.reply_text(mensagem, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ *Comandos disponíveis:*\n\n"
        "🟢 *Básico*\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/meus_dados - Ver seus dados cadastrados\n"
        "/meu_estilo - Ver estilo e tipo de negócio salvos\n"
        "/meuplano - Ver informações do seu plano atual\n\n"
        "📝 *Tarefas*\n"
        "/tarefa - Adiciona uma nova tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/listar_prioridade - Lista tarefas por prioridade\n"
        "/limpar - Remove todas as tarefas\n\n"
        "📅 *Agenda e Eventos*\n"
        "/agenda - Adiciona um novo evento\n"
        "/eventos - Lista eventos agendados\n"
        "/confirmar_reuniao - Confirma uma reunião\n"
        "/confirmar_presenca - Confirma presença em um evento\n"
        "/debug_eventos - Verifica eventos internos\n\n"
        "📧 *E-mails*\n"
        "/conectar_email - Conectar seu e-mail (Google)\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail\n"
        "/meu_email - Define o e-mail de envio manual\n\n"
        "📊 *Relatórios*\n"
        "/relatorio_diario - Gera relatório diário\n"
        "/relatorio_semanal - Gera relatório semanal\n"
        "/enviar_agenda_excel - Exporta a agenda em Excel\n\n"
        "🗣️ *Comando por voz*\n"
        "Envie áudio com pedidos (ex.: “nova tarefa pagar contas”, “agendar corte amanhã 10h com Carla”).\n\n"
        "🔁 *Avisos e Follow-ups*\n"
        "/configuraravisos • /verificaravisos • /followup • /meusfollowups\n\n"
        "🎯 *Personalização*\n"
        "/tipo_negocio • /estilo • /nome_negocio • /listar_profissionais\n",
        parse_mode="Markdown"
    )


async def meus_dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente:
        dados_cliente = "\n".join(f"{key}: {value}" for key, value in cliente.items())
        await update.message.reply_text(f"📂 Seus dados:\n{dados_cliente}")
    else:
        await update.message.reply_text("⚠️ Nenhum dado encontrado para sua conta.")


async def custos_api_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    db = firestore.client()

    ID_DONO = "7394370553"  # ajuste se necessário

    if user_id != ID_DONO:
        await update.message.reply_text("⚠️ Este comando está disponível apenas para o administrador do sistema.")
        return

    try:
        docs = db.collection("custos_usuarios").stream()

        total_geral = 0.0
        por_usuario = {}

        for doc in docs:
            data = doc.to_dict()
            uid = data.get("user_id", "desconhecido")
            custo = float(data.get("custo_usd", 0.0) or 0.0)

            if uid not in por_usuario:
                por_usuario[uid] = {"custo": 0.0, "reqs": 0}

            por_usuario[uid]["custo"] += custo
            por_usuario[uid]["reqs"] += 1
            total_geral += custo

        if not por_usuario:
            await update.message.reply_text("🔍 Nenhum uso registrado da API ainda.")
            return

        linhas = [f"👤 {uid}: {info['reqs']} reqs – ${info['custo']:.4f}" for uid, info in por_usuario.items()]
        texto = "\n".join(linhas)

        resposta = (
            f"📊 *Resumo total de uso da API (todos os usuários)*\n\n"
            f"{texto}\n\n"
            f"💰 *Total geral:* ${total_geral:.4f}"
        )
        await update.message.reply_text(resposta, parse_mode="Markdown")
    except Exception as e:
        logger.exception("❌ Erro ao consultar custos da API")
        await update.message.reply_text("❌ Ocorreu um erro ao consultar os dados.")


# ============== REGISTRO DOS HANDLERS ==============

def register_handlers(application: Application):
    logger.info("✅ Registrando handlers...")

    # 1) DEBUG (grupo 0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _debug_primeiro_handler), group=0)

    # 2) COMANDOS
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("meus_dados", meus_dados))
    application.add_handler(CommandHandler("meuestilo", meu_estilo))
    application.add_handler(CommandHandler("meuplano", meu_plano))
    application.add_handler(CommandHandler("custosapi", custos_api_handler))

    # tarefas
    application.add_handler(CommandHandler("tarefa", add_task))
    application.add_handler(CommandHandler("listar", list_tasks))
    application.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
    application.add_handler(CommandHandler("limpar", clear_tasks))

    # e-mails
    application.add_handler(CommandHandler(["ler_emails", "leremails"], ler_emails_command))
    application.add_handler(CommandHandler(["emails_prioritarios", "emailsprioritarios"], listar_emails_prioritarios))
    application.add_handler(CommandHandler(["conectar_email", "conectaremail"], conectar_email))

    # agenda/eventos
    application.add_handler(CommandHandler("agenda", add_agenda))
    application.add_handler(CommandHandler("eventos", list_events))
    application.add_handler(CommandHandler(["confirmar_reuniao", "confirmarreuniao"], confirmar_reuniao))
    application.add_handler(CommandHandler(["confirmar_presenca", "confirmarpresenca"], confirmar_presenca))
    application.add_handler(CommandHandler("debug_eventos", debug_eventos))
    application.add_handler(CommandHandler("enviar_agenda_excel", enviar_agenda_excel))
    application.add_handler(CommandHandler("cancelar", cancelar_evento_cmd))

    # relatórios  ✅ (comente se não existir no seu repo)
    application.add_handler(CommandHandler(["relatorio_diario", "relatoriodiario"], relatorio_diario))
    application.add_handler(CommandHandler(["relatorio_semanal", "relatoriosemanal"], relatorio_semanal))
    application.add_handler(CommandHandler("enviar_relatorio_email", enviar_relatorio_email))

    # perfil/negócio
    application.add_handler(CommandHandler(["tipo_negocio", "tiponegocio"], set_tipo_negocio))
    application.add_handler(CommandHandler(["estilo"], set_estilo_mensagem))
    application.add_handler(CommandHandler(["nome_negocio", "nomenegocio"], set_nome_negocio))
    application.add_handler(CommandHandler(["tipo_usuario", "tipousuario"], set_tipo_usuario))
    application.add_handler(CommandHandler(["modo_uso", "modouso"], set_modo_uso))
    application.add_handler(CommandHandler(["listar_profissionais", "listarprofissionais"], listar_profissionais))

    # voz
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # followups/avisos
    application.add_handler(CommandHandler("followup", criar_followup))
    application.add_handler(CommandHandler("meusfollowups", listar_followups))
    application.add_handler(CommandHandler("verificaravisos", verificar_avisos))
    application.add_handler(CommandHandler("configuraravisos", configurar_avisos))
    application.add_handler(CommandHandler("testaravisos", testar_avisos))

    # importação (xlsx/csv)
    application.add_handler(MessageHandler(
        filters.Document.MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        importar_profissionais_handler
    ))
    application.add_handler(MessageHandler(
        filters.Document.MimeType("text/csv"),
        importar_profissionais_handler
    ))

    # TEXTO LIVRE (ordem dos pipelines)
    so_texto_nao_num = filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^\d+$")
    application.add_handler(MessageHandler(so_texto_nao_num, tratar_mensagens_gerais), group=10)
    application.add_handler(MessageHandler(so_texto_nao_num, handle_pedido_encaixe), group=20)
    application.add_handler(MessageHandler(so_texto_nao_num, handle_resposta_reagendamento), group=21)

    # testes firebase
    application.add_handler(CommandHandler("testar_firebase", testar_firebase))
    application.add_handler(CommandHandler("verificar_firebase", verificar_firebase))

    logger.info("✅ Handlers registrados com sucesso!")
