import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from handlers.task_handler import add_task, list_tasks, list_tasks_by_priority, clear_tasks
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, enviar_email_command, conectar_email, auth_callback
from handlers.event_handler import add_agenda, list_events, confirmar_reuniao, confirmar_presenca, debug_eventos
from services.firebase_service import buscar_cliente, salvar_cliente
from handlers.test_handler import testar_firebase, testar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import set_tipo_negocio, set_estilo_mensagem, set_nome_negocio, meu_estilo, set_email, meu_plano
from handlers.voice_handler import handle_voice
from handlers.followup_handler import criar_followup, listar_followups, verificar_avisos
from handlers.test_handler import testar_avisos

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)

    dados = {
        "nome": f"{user.first_name} {user.last_name or ''}".strip(),
        "email": "",  # pode ser preenchido depois com /meuemail
    }

    salvar_cliente(user_id, dados)

    await update.message.reply_text(
        f"👋 Olá, {user.first_name}! Sou sua assistente virtual.\n\n"
        f"Digite /help para ver tudo que posso fazer por você."
    )

# ✅ Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ *Comandos disponíveis:*\n\n"
        "🟢 *Básico*\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/meus_dados - Ver seus dados cadastrados\n"
        "/meu_estilo - Ver estilo e tipo de negócio salvos\n\n"

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
        "/auth_callback - Finaliza autenticação de e-mail\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail (por nome ou e-mail)\n"
        "/meu_email - Define e-mail de envio manual\n\n"

        "📊 *Relatórios*\n"
        "/relatorio_diario - Gera relatório diário\n"
        "/relatorio_semanal - Gera relatório semanal\n"
        "/enviar_relatorio_email - Envia relatório por e-mail\n\n"

        "🎯 *Personalização*\n"
        "/tipo_negocio - Define o tipo de negócio\n"
        "/estilo - Define o estilo de mensagens\n"
        "/nome_negocio - Define o nome do seu negócio\n",
        parse_mode='Markdown'
    )

# ✅ Comando /meus_dados
async def meus_dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)

    if cliente:
        dados_cliente = "\n".join(f"{key}: {value}" for key, value in cliente.items())
        await update.message.reply_text(f"📂 Seus dados:\n{dados_cliente}")
    else:
        await update.message.reply_text("⚠️ Nenhum dado encontrado para sua conta.")

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("limpar", clear_tasks))
        application.add_handler(CommandHandler("ler_emails","leremails", ler_emails_command))
        application.add_handler(CommandHandler("emails_prioritarios","emailsprioritarios", listar_emails_prioritarios))
        application.add_handler(CommandHandler("enviar_email","enviaremail", enviar_email_command))
        application.add_handler(CommandHandler("agenda", add_agenda))
        application.add_handler(CommandHandler("eventos", list_events))
        application.add_handler(CommandHandler("confirmar_reuniao","confirmarreuniao", confirmar_reuniao))
        application.add_handler(CommandHandler("confirmar_presenca","confirmarpresenca", confirmar_presenca))
        application.add_handler(CommandHandler("meus_dados", meus_dados, "meusdados"))
        application.add_handler(CommandHandler("conectar_email","conectaremail", conectar_email))
        application.add_handler(CommandHandler("auth_callback", auth_callback))
        application.add_handler(CommandHandler("debug_eventos", debug_eventos))
        application.add_handler(CommandHandler("relatorio_diario", "relatoriodiario", relatorio_diario))
        application.add_handler(CommandHandler("relatorio_semanal", "relatoriosemanal", relatorio_semanal))
        application.add_handler(CommandHandler("enviar_relatorio_email", "enviarrelatorioemail", enviar_relatorio_email))
        application.add_handler(CommandHandler("tipo_negocio", set_tipo_negocio))
        application.add_handler(CommandHandler("estilo", set_estilo_mensagem))
        application.add_handler(CommandHandler("nome_negocio", set_nome_negocio))
        application.add_handler(CommandHandler("meu_estilo", meu_estilo))
        application.add_handler(CommandHandler("meu_email", set_email))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(CommandHandler("meuplano", meu_plano))
        application.add_handler(CommandHandler("followup", criar_followup))
        application.add_handler(CommandHandler("meusfollowups", listar_followups))
        application.add_handler(CommandHandler("verificaravisos", verificar_avisos))
        application.add_handler(CommandHandler("testaravisos", testar_avisos))

        # 🚀 Adicionando os comandos de teste do Firebase
        application.add_handler(CommandHandler("testar_firebase", testar_firebase))
        application.add_handler(CommandHandler("verificar_firebase", verificar_firebase))

        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)