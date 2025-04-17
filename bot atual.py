import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# ✅ Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🚀 Handler do /start foi acionado!")  # TESTE
    logger.debug("🚀 Handler do /start foi acionado!")
    await update.message.reply_text("👋 Olá! Bot funcionando via Webhooks!")

# ✅ Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📖 Handler do /help foi acionado!")  # TESTE
    logger.debug("📖 Handler do /help foi acionado!")
    await update.message.reply_text(
        ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/ping - Testa se o bot está ativo"
    )

# ✅ Comando /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🏓 Handler do /ping foi acionado!")  # TESTE
    logger.debug("🏓 Handler do /ping foi acionado!")
    await update.message.reply_text("🏓 Pong!")

# 🚀 Registra os handlers
def register_handlers(application: Application):
    print("✅ Registrando handlers...")  # TESTE
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    print("✅ Handlers registrados!")  # TESTE
    logger.info("✅ Handlers registrados com sucesso!")
