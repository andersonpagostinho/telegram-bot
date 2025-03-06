import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task, list_tasks, list_tasks_by_priority, clear_tasks
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, enviar_email_command
from handlers.event_handler import add_agenda, list_events, confirmar_reuniao, confirmar_presenca

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("🚀 Comando /start recebido!")
        await update.message.reply_text("👋 Olá! Bot funcionando via Webhooks!")
    except Exception as e:
        logger.error(f"Erro no /start: {e}", exc_info=True)

# ✅ Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/tarefa - Adiciona uma tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/limpar - Remove todas as tarefas\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail\n"
    )

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("limpar", clear_tasks))
        application.add_handler(CommandHandler("ler_emails", ler_emails_command))
        application.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
        application.add_handler(CommandHandler("enviar_email", enviar_email_command))
        application.add_handler(CommandHandler("agenda", add_agenda))
        application.add_handler(CommandHandler("eventos", list_events))
        application.add_handler(CommandHandler("confirmar_reuniao", confirmar_reuniao))
        application.add_handler(CommandHandler("confirmar_presenca", confirmar_presenca))

        logger.info("✅ Handlers registrados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)
