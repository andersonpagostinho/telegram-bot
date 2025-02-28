import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from handlers.task_handler import add_task, list_tasks, list_tasks_by_priority, clear_tasks
from handlers.event_handler import add_agenda, list_events, confirmar_reuniao, confirmar_presenca
from handlers.email_handler import ler_emails_command, listar_emails_prioritarios, enviar_email_command, priorizar_email
from handlers.report_handler import relatorio_diario, relatorio_semanal

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
        "/ping - Testa se o bot está ativo\n"
        "/tarefa - Adiciona uma tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/listar_prioridade - Lista tarefas ordenadas por prioridade\n"
        "/limpar - Remove todas as tarefas\n"
        "/agenda - Agenda um evento\n"
        "/eventos - Lista todos os eventos\n"
        "/confirmar_reuniao - Confirma um evento agendado\n"
        "/confirmar_presenca - Confirma presença em um evento\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail\n"
        "/priorizar_email - Configura priorização de e-mails\n"
        "/relatorio_diario - Gera um relatório diário\n"
        "/relatorio_semanal - Gera um relatório semanal\n"
        "/editar_tarefa - Edita a prioridade de uma tarefa"
    )

# ✅ Comando /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🏓 Comando /ping recebido!")
    await update.message.reply_text("🏓 Pong!")

# 🚀 Registra os handlers
def register_handlers(application: Application):
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping))
        application.add_handler(CommandHandler("tarefa", add_task))
        application.add_handler(CommandHandler("listar", list_tasks))
        application.add_handler(CommandHandler("listar_prioridade", list_tasks_by_priority))
        application.add_handler(CommandHandler("limpar", clear_tasks))
        application.add_handler(CommandHandler("agenda", add_agenda))
        application.add_handler(CommandHandler("eventos", list_events))
        application.add_handler(CommandHandler("confirmar_reuniao", confirmar_reuniao))
        application.add_handler(CommandHandler("confirmar_presenca", confirmar_presenca))
        application.add_handler(CommandHandler("ler_emails", ler_emails_command))
        application.add_handler(CommandHandler("emails_prioritarios", listar_emails_prioritarios))
        application.add_handler(CommandHandler("enviar_email", enviar_email_command))
        application.add_handler(CommandHandler("priorizar_email", priorizar_email))
        application.add_handler(CommandHandler("relatorio_diario", relatorio_diario))
        application.add_handler(CommandHandler("relatorio_semanal", relatorio_semanal))
        
        logger.info("✅ Handlers registrados com sucesso!")
        logger.debug("Todos os handlers foram adicionados corretamente.")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)