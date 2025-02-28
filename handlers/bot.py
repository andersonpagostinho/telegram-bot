import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("🚀 Comando /start recebido!")
        await update.message.reply_text("👋 Olá! Bot funcionando via Webhooks!")
    except Exception as e:
        logger.error(f"Erro no /start: {e}", exc_info=True)  # Log com traceback

# ✅ Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/ping - Testa se o bot está ativo"
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
        logger.info("✅ Handlers registrados com sucesso!")
        logger.debug("Handlers: /start, /help, /ping")  # Log detalhado
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers: {e}", exc_info=True)  # Log de erro com traceback
